from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass, field
import re
from typing import Any

from core.workspace_manager import WorkspaceManager


VERIFIED = "VERIFIED"
UNVERIFIED = "UNVERIFIED"
CONTRADICTED = "CONTRADICTED"


@dataclass(frozen=True)
class TranscriptSegment:
    text: str
    speaker: str | None = None
    start_seconds: float | None = None
    end_seconds: float | None = None


@dataclass(frozen=True)
class Decision:
    text: str
    source: TranscriptSegment


@dataclass(frozen=True)
class ActionItem:
    text: str
    owner: str | None
    deadline: str | None
    source: TranscriptSegment


@dataclass(frozen=True)
class ClaimEvidence:
    claim: str
    status: str
    evidence: str | None = None


@dataclass
class MeetingAnalysis:
    transcript: list[TranscriptSegment]
    topics: list[str] = field(default_factory=list)
    claims: list[str] = field(default_factory=list)
    decisions: list[Decision] = field(default_factory=list)
    action_items: list[ActionItem] = field(default_factory=list)
    evidence: list[ClaimEvidence] = field(default_factory=list)
    final_document: dict[str, Any] | None = None


class MeetingAgent:
    """Meeting analysis agent scaffold with explicit privacy and evidence handling."""

    def __init__(self, workspace: WorkspaceManager | None = None):
        self.workspace = workspace or WorkspaceManager()
        self.state = "IDLE"
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="athena-meeting")

    def intake_transcript(self, transcript: str | list[TranscriptSegment]) -> list[TranscriptSegment]:
        if isinstance(transcript, str):
            return [TranscriptSegment(text=line.strip()) for line in transcript.splitlines() if line.strip()]
        return list(transcript)

    def extract_topics_and_claims(self, transcript: list[TranscriptSegment]) -> MeetingAnalysis:
        topics: list[str] = []
        claims: list[str] = []
        topic_markers = ("about", "topic", "discuss", "focus", "agenda")
        claim_markers = ("will", "must", "need to", "agreed", "because", "is ", "are ")

        for segment in transcript:
            text = re.sub(r"\s+", " ", segment.text).strip()
            lowered = text.lower()
            if any(marker in lowered for marker in topic_markers):
                topics.append(text)
            if any(marker in lowered for marker in claim_markers):
                claims.append(text)

        return MeetingAnalysis(transcript=transcript, topics=list(dict.fromkeys(topics)), claims=list(dict.fromkeys(claims)))

    def extract_decisions(self, transcript: list[TranscriptSegment]) -> list[Decision]:
        markers = ("decision:", "decided:", "we decided", "agreed to", "approved:")
        return [
            Decision(text=segment.text.strip(), source=segment)
            for segment in transcript
            if any(marker in segment.text.lower() for marker in markers)
        ]

    def extract_action_items(self, transcript: list[TranscriptSegment]) -> list[ActionItem]:
        action_pattern = re.compile(r"^(?:action item|action|todo|to-do)\s*:\s*(?P<text>.+)$", re.IGNORECASE)
        owner_pattern = re.compile(r"^(?P<owner>[A-Za-z][\w -]{0,49})\s+(?:will|must|needs to)\b", re.IGNORECASE)
        deadline_pattern = re.compile(r"\b(?:by|before|due)\s+(?P<deadline>[^,.!?]+)", re.IGNORECASE)
        items: list[ActionItem] = []
        for segment in transcript:
            match = action_pattern.match(segment.text.strip())
            if not match:
                continue
            text = match.group("text").strip()
            owner_match = owner_pattern.match(text)
            deadline_match = deadline_pattern.search(text)
            items.append(
                ActionItem(
                    text=text,
                    owner=owner_match.group("owner").strip() if owner_match else segment.speaker,
                    deadline=deadline_match.group("deadline").strip() if deadline_match else None,
                    source=segment,
                )
            )
        return items

    def verify_claims(self, claims: list[str], evidence: dict[str, str] | None = None) -> list[ClaimEvidence]:
        """Classify claims using caller-supplied simulated evidence only."""
        records: list[ClaimEvidence] = []
        for claim in claims:
            evidence_text = (evidence or {}).get(claim)
            if not evidence_text:
                status = UNVERIFIED
            elif re.search(r"\b(?:contradicts|contradicted|false|not true|denies)\b", evidence_text, re.IGNORECASE):
                status = CONTRADICTED
            else:
                status = VERIFIED
            records.append(ClaimEvidence(claim=claim, status=status, evidence=evidence_text))
        return records

    def generate_final_document(self, analysis: MeetingAnalysis) -> dict[str, Any]:
        """Build a document from extracted values; do not infer missing meeting facts."""
        return {
            "topics": list(analysis.topics),
            "claims": [
                {"text": item.claim, "status": item.status, "evidence": item.evidence}
                for item in analysis.evidence
            ],
            "decisions": [item.text for item in analysis.decisions],
            "action_items": [
                {"text": item.text, "owner": item.owner, "deadline": item.deadline}
                for item in analysis.action_items
            ],
        }

    def process_transcript(
        self,
        transcript: str | list[TranscriptSegment],
        evidence: dict[str, str] | None = None,
    ) -> MeetingAnalysis:
        self.state = "PROCESSING"
        segments = self.intake_transcript(transcript)
        result = self.extract_topics_and_claims(segments)
        result.decisions = self.extract_decisions(segments)
        result.action_items = self.extract_action_items(segments)
        result.evidence = self.verify_claims(result.claims, evidence)
        result.final_document = self.generate_final_document(result)
        self.state = "READY"
        return result

    def process_transcript_background(
        self,
        transcript: str | list[TranscriptSegment],
        evidence: dict[str, str] | None = None,
    ) -> Future[MeetingAnalysis]:
        return self._executor.submit(self.process_transcript, transcript, evidence)

    def close(self) -> None:
        self._executor.shutdown(wait=True)

    def plan_meeting(self, request: str) -> dict[str, Any]:
        self.state = "ANALYZING"
        return {
            "agent": "meeting",
            "state": "READY",
            "request": request,
            "workflow": [
                "allowed transcript intake",
                "topic extraction",
                "claim extraction",
                "decision extraction",
                "action-item extraction",
                "evidence checks",
                "professional summary",
            ],
            "privacy_required": True,
        }
