from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Any

from core.workspace_manager import WorkspaceManager


NEW = "NEW"
REVIEW_REQUIRED = "REVIEW_REQUIRED"
APPROVED = "APPROVED"
REJECTED = "REJECTED"


@dataclass(frozen=True)
class JobPosting:
    title: str
    company: str
    location: str = ""
    description: str = ""
    url: str = ""
    source: str = ""


@dataclass(frozen=True)
class JobProfile:
    title: str
    required_skills: list[str] = field(default_factory=list)
    preferred_skills: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ResumeProfile:
    name: str = ""
    skills: list[str] = field(default_factory=list)
    experience: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class MatchResult:
    score: float
    alignments: list[str]
    gaps: list[str]


@dataclass
class TrackedJob:
    posting: JobPosting
    match: MatchResult
    state: str = NEW


class JobSource:
    """Adapter contract for a job provider; network behavior belongs in adapters."""

    name = "source"

    def fetch_jobs(self, query: str) -> list[JobPosting]:
        raise NotImplementedError


class JobAgent:
    """Job discovery, explainable matching, and approval-gated tracking."""

    def __init__(self, workspace: WorkspaceManager | None = None):
        self.workspace = workspace or WorkspaceManager()
        self.state = "IDLE"
        self._sources: dict[str, JobSource] = {}
        self._jobs: dict[str, TrackedJob] = {}

    def register_source(self, source: JobSource) -> None:
        self._sources[source.name] = source

    @staticmethod
    def _normalize(value: str) -> str:
        return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()

    def _dedupe_key(self, posting: JobPosting) -> str:
        if posting.url.strip():
            return f"url:{posting.url.strip().lower().rstrip('/')}"
        return "job:" + "|".join(
            self._normalize(value)
            for value in (posting.company, posting.title, posting.location)
        )

    def discover_jobs(self, query: str, source_names: list[str] | None = None) -> list[JobPosting]:
        selected = source_names or list(self._sources)
        unique: dict[str, JobPosting] = {}
        for name in selected:
            source = self._sources.get(name)
            if source is None:
                raise ValueError(f"Unknown job source: {name}")
            for posting in source.fetch_jobs(query):
                unique.setdefault(self._dedupe_key(posting), posting)
        return list(unique.values())

    @staticmethod
    def _known_skills(text: str) -> list[str]:
        vocabulary = (
            "python", "sql", "javascript", "typescript", "react", "java", "c++",
            "aws", "azure", "docker", "kubernetes", "machine learning", "data analysis",
            "project management", "communication", "excel",
        )
        lowered = text.lower()
        return [skill for skill in vocabulary if re.search(rf"(?<!\w){re.escape(skill)}(?!\w)", lowered)]

    def parse_job_description(self, posting: JobPosting) -> JobProfile:
        skills = self._known_skills(posting.description)
        required_text = re.search(
            r"(?:required|must have|qualifications?)\s*:?\s*(.*?)(?=\bpreferred\b|\bnice to have\b|$)",
            posting.description,
            re.IGNORECASE,
        )
        preferred_text = re.search(r"(?:preferred|nice to have)\s*:?\s*(.*)", posting.description, re.IGNORECASE)
        required = self._known_skills(required_text.group(1)) if required_text else skills
        preferred = self._known_skills(preferred_text.group(1)) if preferred_text else []
        return JobProfile(title=posting.title, required_skills=required, preferred_skills=preferred)

    def parse_resume(self, resume_text: str, name: str = "") -> ResumeProfile:
        return ResumeProfile(name=name, skills=self._known_skills(resume_text), experience=[line.strip() for line in resume_text.splitlines() if line.strip()])

    def match(self, job: JobProfile, resume: ResumeProfile) -> MatchResult:
        resume_skills = set(resume.skills)
        required = list(dict.fromkeys(job.required_skills))
        alignments = [skill for skill in required if skill in resume_skills]
        gaps = [skill for skill in required if skill not in resume_skills]
        score = round((len(alignments) / len(required)) * 100, 2) if required else 0.0
        return MatchResult(score=score, alignments=alignments, gaps=gaps)

    def queue_for_review(self, posting: JobPosting, match: MatchResult) -> TrackedJob:
        key = self._dedupe_key(posting)
        tracked = TrackedJob(posting=posting, match=match, state=REVIEW_REQUIRED)
        self._jobs[key] = tracked
        return tracked

    def approve_job(self, posting: JobPosting) -> TrackedJob:
        tracked = self._jobs[self._dedupe_key(posting)]
        if tracked.state != REVIEW_REQUIRED:
            raise ValueError("Only jobs awaiting review can be approved")
        tracked.state = APPROVED
        return tracked

    def reject_job(self, posting: JobPosting) -> TrackedJob:
        tracked = self._jobs[self._dedupe_key(posting)]
        if tracked.state != REVIEW_REQUIRED:
            raise ValueError("Only jobs awaiting review can be rejected")
        tracked.state = REJECTED
        return tracked

    def review_queue(self) -> list[TrackedJob]:
        return [job for job in self._jobs.values() if job.state == REVIEW_REQUIRED]

    def plan_job_search(self, request: str) -> dict[str, Any]:
        self.state = "SCANNING"
        return {
            "agent": "job",
            "state": "READY",
            "request": request,
            "workflow": [
                "discover jobs",
                "normalize candidates",
                "compare resume profile",
                "score fit",
                "filter low matches",
                "queue human review",
            ],
            "approval_required": True,
        }
