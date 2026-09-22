from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path


class WorkspaceManager:
    """Small, shared path manager for user-created Atlas projects."""

    def __init__(self, root: str | Path | None = None):
        self.root = Path(root) if root is not None else self._default_root()
        self._state_file = self.root / "memory" / "last_created_path.json" if self.root.name == "Athena_AI_RAG_Assistant" else self.root / ".atlas" / "last_created_path.json"
        self._state_file.parent.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _default_root() -> Path:
        if getattr(sys, "frozen", False):
            return Path(sys.executable).parent
        return Path(__file__).resolve().parent.parent

    @staticmethod
    def home() -> Path:
        return Path.home()

    @staticmethod
    def desktop() -> Path:
        return Path.home() / "Desktop"

    @staticmethod
    def documents() -> Path:
        return Path.home() / "Documents"

    @staticmethod
    def downloads() -> Path:
        return Path.home() / "Downloads"

    def resolve_user_path(self, raw: str) -> Path:
        text = (raw or "").strip().strip('"').strip("'")
        if not text:
            return self.desktop()

        lower = text.lower()
        shortcuts = {
            "desktop": self.desktop(),
            "documents": self.documents(),
            "downloads": self.downloads(),
            "home": Path.home(),
            "workspace": self.root,
            "project": self.root,
            "atlas": self.root,
        }
        if lower in shortcuts:
            return shortcuts[lower]

        if lower.startswith("desktop/") or lower.startswith("desktop\\"):
            rel = text.split("/", 1)[1] if "/" in text else text.split("\\", 1)[1]
            return self.desktop() / rel
        if lower.startswith("documents/") or lower.startswith("documents\\"):
            rel = text.split("/", 1)[1] if "/" in text else text.split("\\", 1)[1]
            return self.documents() / rel
        if lower.startswith("downloads/") or lower.startswith("downloads\\"):
            rel = text.split("/", 1)[1] if "/" in text else text.split("\\", 1)[1]
            return self.downloads() / rel

        if re.match(r"^[a-zA-Z]:[/\\]?$", text):
            return Path(text.upper().replace("\\", "/"))

        if os.path.isabs(text):
            return Path(text).expanduser()

        return (self.root / text).expanduser() if not text.startswith(".") else Path(text).expanduser()

    def create_directory(self, base: str, name: str) -> Path:
        target = self.resolve_user_path(base) / name
        target.mkdir(parents=True, exist_ok=True)
        self._remember_created_path(target)
        return target.resolve(strict=False)

    def create_file(self, base: str, name: str, content: str = "") -> Path:
        target = self.resolve_user_path(base) / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        self._remember_created_path(target)
        return target.resolve(strict=False)

    def _remember_created_path(self, target: Path) -> None:
        try:
            self._state_file.parent.mkdir(parents=True, exist_ok=True)
            self._state_file.write_text(json.dumps({"path": str(target.resolve(strict=False))}, ensure_ascii=False), encoding="utf-8")
        except Exception:
            pass

    def last_created_path(self) -> Path | None:
        try:
            if not self._state_file.exists():
                return None
            payload = json.loads(self._state_file.read_text(encoding="utf-8"))
            path = payload.get("path")
            if not path:
                return None
            target = Path(path).expanduser()
            if target.exists():
                return target.resolve(strict=False)
        except Exception:
            return None
        return None
