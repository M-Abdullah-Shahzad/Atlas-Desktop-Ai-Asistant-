import sys
import types
import unittest
from unittest.mock import patch

import numpy as np

from core.stt import (
    WhisperSTT,
    _filter_english_transcript,
    _has_voice_activity,
    _normalize_transcript,
)


class SttTests(unittest.TestCase):
    def test_non_english_scripts_are_rejected(self):
        for text in ("नमस्ते", "ਸਤ ਸ੍ਰੀ ਅਕਾਲ", "안녕하세요"):
            self.assertEqual(_filter_english_transcript(text), "")

    def test_english_text_survives_normalization(self):
        self.assertEqual(_normalize_transcript("  Hello, Atlas!  "), "Hello, Atlas!")

    def test_silence_and_repeated_hallucinations_are_rejected(self):
        self.assertFalse(_has_voice_activity(np.zeros(1600, dtype=np.float32)))
        self.assertEqual(_filter_english_transcript("hello hello hello hello"), "")
        self.assertEqual(_filter_english_transcript("thanks for watching"), "")

    def test_whisper_language_is_always_english(self):
        class FakeModel:
            def __init__(self):
                self.language = None

            def transcribe(self, audio, **kwargs):
                self.language = kwargs["language"]
                return [], None

        fake_model = FakeModel()
        fake_module = types.SimpleNamespace(WhisperModel=lambda *args, **kwargs: fake_model)
        with patch.dict(sys.modules, {"faster_whisper": fake_module}):
            engine = WhisperSTT(language="ko")
            engine.transcribe(np.full(1600, 0.02, dtype=np.float32))

        self.assertEqual(engine._language, "en")
        self.assertEqual(fake_model.language, "en")


if __name__ == "__main__":
    unittest.main()
