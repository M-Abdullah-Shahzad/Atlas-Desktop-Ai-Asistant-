"""
Speech-to-Text engines for MARK XL.

Whisper  – offline transcription via faster-whisper (VAD-buffered)
Vosk     – offline streaming transcription (lighter)
"""
import json
import re
import unicodedata

import numpy as np


_SILENCE_RMS = 0.003
_HALLUCINATION_PHRASES = {
    "thank you for watching",
    "thanks for watching",
    "please subscribe",
}


def _has_voice_activity(audio: np.ndarray) -> bool:
    """Reject empty or effectively silent buffers before invoking the model."""
    samples = np.asarray(audio, dtype=np.float32)
    if samples.size == 0 or not np.isfinite(samples).any():
        return False
    finite = samples[np.isfinite(samples)]
    rms = float(np.sqrt(np.mean(np.square(finite))))
    peak = float(np.max(np.abs(finite)))
    return rms >= _SILENCE_RMS and peak >= _SILENCE_RMS * 2


def _filter_english_transcript(text: str) -> str:
    """Keep plausible English text and discard script/language hallucinations."""
    if not text:
        return ""
    if any(char.isalpha() and not ("A" <= char <= "Z" or "a" <= char <= "z") for char in text):
        return ""

    words = re.findall(r"[A-Za-z]+(?:'[A-Za-z]+)?", text.lower())
    if not words:
        return ""
    if text.lower().strip() in _HALLUCINATION_PHRASES:
        return ""
    if len(words) >= 4 and len(set(words)) == 1:
        return ""
    return text


def _normalize_transcript(text: str) -> str:
    """Normalize noisy transcript output without destroying valid English text."""
    if not isinstance(text, str):
        return ""

    cleaned = unicodedata.normalize("NFKC", text)
    cleaned = cleaned.replace("\r", " ").replace("\n", " ")
    cleaned = (cleaned.replace("’", "'")
        .replace("‘", "'")
        .replace("“", '"')
        .replace("”", '"')
        .replace("–", "-")
        .replace("—", " - "))
    cleaned = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned)
    cleaned = re.sub(r"\s+([,.;:?!])", r"\1", cleaned)
    cleaned = cleaned.strip()
    return _filter_english_transcript(cleaned)


class WhisperSTT:
    """Offline transcription using faster-whisper."""

    def __init__(self, model_name: str = "base", language: str | None = "en"):
        import os
        from faster_whisper import WhisperModel
        print(f"[STT] Loading Whisper '{model_name}'…")
        try:
            import torch
            device  = "cuda" if torch.cuda.is_available() else "cpu"
            compute = "float16" if device == "cuda" else "int8"
        except Exception:
            device, compute = "cpu", "int8"

        try:
            self._model = WhisperModel(model_name, device=device, compute_type=compute)
        except Exception as _first_err:
            # Offline flag set but model not cached yet → clear flags and download once.
            # Keywords cover multiple huggingface_hub error message variants across versions.
            _e = str(_first_err).lower()
            _offline_keywords = (
                "offline", "not found", "cache", "localentry",
                "does not exist", "outgoing", "local_files_only",
            )
            if any(k in _e for k in _offline_keywords):
                print(f"[STT] Whisper '{model_name}' not in local cache — downloading (one-time, internet required)…")
                os.environ.pop("HF_HUB_OFFLINE",      None)
                os.environ.pop("TRANSFORMERS_OFFLINE", None)
                os.environ.pop("HF_DATASETS_OFFLINE",  None)
                try:
                    self._model = WhisperModel(model_name, device=device, compute_type=compute)
                except Exception as _dl_err:
                    raise RuntimeError(
                        f"Whisper '{model_name}' model download failed.\n"
                        f"Internet access is required the first time to download the speech model (~75–290 MB).\n"
                        f"After the first download it runs fully offline.\n"
                        f"Details: {_dl_err}"
                    ) from _dl_err
            else:
                raise

        # Atlas voice input is intentionally English-only; never let model language detection switch scripts.
        self._language = "en"
        print(f"[STT] Whisper '{model_name}' ready ({device})")

    def transcribe(self, audio: np.ndarray) -> str:
        """Transcribe a float32 mono 16 kHz numpy array. Returns transcript string."""
        if not _has_voice_activity(audio):
            return ""
        try:
            segments, _ = self._model.transcribe(
                audio,
                language=self._language,
                beam_size=1,                       # greedy — 2-3x faster
                best_of=1,
                condition_on_previous_text=False,  # no hallucinations, faster
                vad_filter=True,
                vad_parameters={"min_silence_duration_ms": 300},
            )
            text = " ".join(s.text for s in segments).strip()
            return _normalize_transcript(text)
        except Exception as e:
            print(f"[STT] Transcription error: {e}")
            raise


class VoskSTT:
    """Streaming transcription using Vosk."""

    def __init__(self, model_path: str | None = None, language: str = "en-us"):
        from vosk import Model, KaldiRecognizer
        print("[STT] Loading Vosk model…")
        if model_path:
            model = Model(model_path)
        else:
            model = Model(lang="en-us")
        self._rec = KaldiRecognizer(model, 16000)
        print("[STT] Vosk ready.")

    def process_chunk(self, audio_bytes: bytes) -> tuple[str, bool]:
        """Feed raw int16 LE PCM bytes. Returns (text, is_final)."""
        if not audio_bytes:
            return "", False
        samples = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32768.0
        if not _has_voice_activity(samples):
            return "", False
        if self._rec.AcceptWaveform(audio_bytes):
            result = json.loads(self._rec.Result())
            return _normalize_transcript(result.get("text", "")), True
        partial = json.loads(self._rec.PartialResult())
        return _normalize_transcript(partial.get("partial", "")), False
