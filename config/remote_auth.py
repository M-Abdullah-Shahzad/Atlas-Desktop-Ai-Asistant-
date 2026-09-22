"""Persistent remote-access password for the phone dashboard."""

from __future__ import annotations

import hashlib
import json
import secrets
import sys
from pathlib import Path


def _app_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


REMOTE_CONFIG_FILE = _app_root() / "config" / "remote.json"
_PBKDF2_ITERS = 200_000


def load_remote_config() -> dict:
    try:
        if REMOTE_CONFIG_FILE.exists():
            data = json.loads(REMOTE_CONFIG_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
    except Exception:
        pass
    return {}


def save_remote_config(data: dict) -> None:
    if not isinstance(data, dict):
        return
    REMOTE_CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    temp_path = REMOTE_CONFIG_FILE.with_suffix(".json.tmp")
    temp_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    temp_path.replace(REMOTE_CONFIG_FILE)


def has_remote_password() -> bool:
    d = load_remote_config()
    salt = str(d.get("password_salt") or "")
    expected = str(d.get("password_hash") or "")
    if len(salt) != 32 or len(expected) != 64:
        return False
    try:
        return len(bytes.fromhex(salt)) == 16
    except ValueError:
        return False


def get_command_key() -> str:
    d = load_remote_config()
    key = str(d.get("command_key") or "").strip()
    if key:
        return key
    key = secrets.token_urlsafe(24)
    d["command_key"] = key
    save_remote_config(d)
    return key


def set_remote_password(password: str) -> None:
    password = str(password or "").strip()
    if not password:
        return
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        bytes.fromhex(salt),
        _PBKDF2_ITERS,
    ).hex()
    d = load_remote_config()
    d["password_salt"] = salt
    d["password_hash"] = digest
    d["pbkdf2_iters"] = _PBKDF2_ITERS
    if not str(d.get("command_key") or "").strip():
        d["command_key"] = secrets.token_urlsafe(24)
    save_remote_config(d)


def verify_remote_password(password: str) -> bool:
    d = load_remote_config()
    salt = str(d.get("password_salt") or "")
    expected = str(d.get("password_hash") or "")
    try:
        iters = int(d.get("pbkdf2_iters") or _PBKDF2_ITERS)
    except (TypeError, ValueError):
        iters = _PBKDF2_ITERS
    if iters <= 0:
        iters = _PBKDF2_ITERS
    if len(salt) != 32 or len(expected) != 64:
        return False
    try:
        salt_bytes = bytes.fromhex(salt)
    except ValueError:
        return False
    if len(salt_bytes) != 16:
        return False
    try:
        digest = hashlib.pbkdf2_hmac(
            "sha256",
            str(password or "").encode("utf-8"),
            salt_bytes,
            iters,
        ).hex()
    except Exception:
        return False
    return secrets.compare_digest(digest, expected)
