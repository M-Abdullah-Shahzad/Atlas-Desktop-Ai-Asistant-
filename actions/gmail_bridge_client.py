"""
Gmail API bridge for Athena — OAuth + messages.send (no browser GUI).

Setup:
  1. Google Cloud Console → create OAuth client (Desktop app)
  2. Put client_id + client_secret in config/api_keys.json under "gmail"
  3. Run: python actions/gmail_bridge_client.py --login
     (or first compose will open the browser once)
"""

from __future__ import annotations

import base64
import json
import os
import re
import secrets
import sys
import threading
import time
import webbrowser
from email.mime.text import MIMEText
from email.utils import getaddresses
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlencode, urlparse

import requests

SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.settings.basic",
]
AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
GMAIL_SEND_URL = "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"
GMAIL_MESSAGES_URL = "https://gmail.googleapis.com/gmail/v1/users/me/messages"
GMAIL_VACATION_URL = "https://gmail.googleapis.com/gmail/v1/users/me/settings/vacation"
DEFAULT_REDIRECT = "http://127.0.0.1:8766/"
AUTH_PORT = 8766

_auth_bg_lock = threading.Lock()
_auth_bg_started = False


def _base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


def _api_keys_path() -> Path:
    return _base_dir() / "config" / "api_keys.json"


def _token_path() -> Path:
    d = _base_dir() / "memory" / "gmail_oauth"
    d.mkdir(parents=True, exist_ok=True)
    return d / "token.json"


def _load_api_keys() -> dict[str, Any]:
    try:
        from memory.config_manager import load_api_keys

        return load_api_keys()
    except Exception:
        return {}


def _gmail_cfg() -> dict[str, Any]:
    data = _load_api_keys()
    raw = data.get("gmail")
    if isinstance(raw, dict):
        return raw
    return {}


def _save_gmail_fields(**fields: Any) -> None:
    path = _api_keys_path()
    data: dict[str, Any] = {}
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            data = {}
    gmail = data.get("gmail") if isinstance(data.get("gmail"), dict) else {}
    gmail = dict(gmail)
    gmail.update(fields)
    data["gmail"] = gmail
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=4), encoding="utf-8")


def _load_token() -> dict[str, Any]:
    path = _token_path()
    if not path.exists():
        # Fallback: tokens stored under api_keys gmail section
        cfg = _gmail_cfg()
        if cfg.get("access_token"):
            return {
                "access_token": cfg.get("access_token"),
                "refresh_token": cfg.get("refresh_token"),
                "expires_at": cfg.get("expires_at"),
                "token_type": cfg.get("token_type", "Bearer"),
            }
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_token(payload: dict[str, Any], *, keep_refresh: str | None = None) -> None:
    access = payload.get("access_token") or ""
    refresh = payload.get("refresh_token") or keep_refresh or ""
    expires_in = int(payload.get("expires_in") or 3600)
    if not access:
        raise RuntimeError("No access_token in Google response.")
    data = {
        "access_token": access,
        "refresh_token": refresh,
        "expires_at": time.time() + expires_in - 60,
        "token_type": payload.get("token_type") or "Bearer",
        "scope": payload.get("scope") or " ".join(SCOPES),
    }
    path = _token_path()
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _clear_token() -> None:
    path = _token_path()
    try:
        if path.exists():
            path.unlink()
    except Exception:
        pass


def _client_credentials() -> tuple[str, str, str]:
    cfg = _gmail_cfg()
    client_id = str(cfg.get("client_id") or "").strip()
    client_secret = str(cfg.get("client_secret") or "").strip()
    redirect = str(cfg.get("redirect_uri") or DEFAULT_REDIRECT).strip()
    return client_id, client_secret, redirect


def status() -> dict[str, Any]:
    tok = _load_token()
    linked = bool(tok.get("access_token") or tok.get("refresh_token"))
    cfg = _gmail_cfg()
    return {
        "linked": linked,
        "has_client_id": bool(str(cfg.get("client_id") or "").strip()),
        "expires_at": tok.get("expires_at"),
    }


def _port_in_use(port: int) -> bool:
    import socket

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            s.bind(("127.0.0.1", port))
            return False
        except OSError:
            return True


def _auth_url(client_id: str, redirect_uri: str, state: str) -> str:
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
    }
    return f"{AUTH_URL}?{urlencode(params)}"


def _open_in_browser(url: str) -> bool:
    """Open OAuth in the user's browser, including GUI-launched Windows apps."""
    if sys.platform == "win32":
        try:
            os.startfile(url)  # type: ignore[attr-defined]
            return True
        except Exception:
            pass
    try:
        return bool(webbrowser.open(url))
    except Exception:
        return False


def _exchange_code(client_id: str, client_secret: str, code: str, redirect_uri: str) -> dict:
    r = requests.post(
        TOKEN_URL,
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
            "client_id": client_id,
            "client_secret": client_secret,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=20,
    )
    if r.status_code != 200:
        raise RuntimeError(f"Token exchange failed ({r.status_code}): {r.text[:240]}")
    return r.json()


def run_oauth_flow(*, timeout: float = 180.0, open_browser: bool = True) -> str:
    client_id, client_secret, redirect_uri = _client_credentials()
    if not client_id or not client_secret:
        raise RuntimeError(
            "Missing gmail.client_id / gmail.client_secret in config/api_keys.json. "
            "Create an OAuth Desktop client in Google Cloud Console, enable Gmail API, "
            f"add redirect URI {DEFAULT_REDIRECT}, then add the credentials."
        )
    parsed = urlparse(redirect_uri)
    port = parsed.port or AUTH_PORT
    if _port_in_use(port):
        raise RuntimeError(
            f"Port {port} is in use. Free it or change gmail.redirect_uri "
            f"(default {DEFAULT_REDIRECT})."
        )

    state = secrets.token_urlsafe(16)
    box: dict[str, Any] = {"code": None, "error": None, "state": None}

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802
            qs = parse_qs(urlparse(self.path).query)
            box["code"] = (qs.get("code") or [None])[0]
            box["error"] = (qs.get("error") or [None])[0]
            box["state"] = (qs.get("state") or [None])[0]
            ok = bool(box["code"]) and not box["error"]
            body = (
                b"<html><body><h2>Atlas Gmail linked.</h2>"
                b"<p>You can close this tab and return to Atlas.</p></body></html>"
                if ok
                else b"<html><body><h2>Authorization failed.</h2></body></html>"
            )
            self.send_response(200 if ok else 400)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_HEAD(self):  # noqa: N802
            self.send_response(200)
            self.send_header("Content-Length", "0")
            self.end_headers()

        def log_message(self, *_args):
            return

    class CallbackServer(ThreadingHTTPServer):
        allow_reuse_address = True
        daemon_threads = True

    try:
        server = CallbackServer(("127.0.0.1", port), Handler)
    except OSError as exc:
        raise RuntimeError(
            f"Could not start Gmail callback server on 127.0.0.1:{port}: {exc}. "
            "Close any previous Gmail login window and try again."
        ) from exc
    server.timeout = 1.0
    print(f"[Gmail] OAuth callback listening on http://127.0.0.1:{port}/")
    url = _auth_url(client_id, redirect_uri, state)
    if open_browser:
        if not _open_in_browser(url):
            raise RuntimeError(
                "Could not open the Gmail authorization browser. "
                f"Open this URL manually: {url}"
            )
    else:
        print(f"Open this URL to authorize:\n{url}\n")

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline and box["code"] is None and box["error"] is None:
        server.handle_request()
    server.server_close()

    if box["error"]:
        raise RuntimeError(f"Gmail auth error: {box['error']}")
    if not box["code"]:
        raise RuntimeError(
            "Gmail login timed out. Run: python actions/gmail_bridge_client.py --login"
        )
    if box["state"] != state:
        raise RuntimeError("OAuth state mismatch. Try login again.")

    payload = _exchange_code(client_id, client_secret, box["code"], redirect_uri)
    _save_token(payload)
    return "Gmail linked. You can read and send email through Atlas now."


def _refresh_access_token() -> str | None:
    client_id, client_secret, _redir = _client_credentials()
    tok = _load_token()
    refresh = str(tok.get("refresh_token") or "").strip()
    if not client_id or not client_secret or not refresh:
        return None
    r = requests.post(
        TOKEN_URL,
        data={
            "grant_type": "refresh_token",
            "refresh_token": refresh,
            "client_id": client_id,
            "client_secret": client_secret,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=20,
    )
    if r.status_code != 200:
        if r.status_code in (400, 401):
            _clear_token()
        return None
    payload = r.json()
    _save_token(payload, keep_refresh=refresh)
    return str(payload.get("access_token") or "")


def get_access_token(*, interactive: bool = False) -> str | None:
    tok = _load_token()
    access = str(tok.get("access_token") or "").strip()
    expires_at = float(tok.get("expires_at") or 0)
    if access and time.time() < expires_at:
        return access
    refreshed = _refresh_access_token()
    if refreshed:
        return refreshed
    if interactive:
        try:
            run_oauth_flow(timeout=180.0, open_browser=True)
            return str(_load_token().get("access_token") or "") or None
        except Exception as e:
            print(f"[Gmail] OAuth failed: {e}")
            return None
    return None


def ensure_linked(*, interactive: bool = True) -> tuple[bool, str]:
    client_id, client_secret, _ = _client_credentials()
    if not client_id or not client_secret:
        return False, (
            "AUTH_REQUIRED: Add gmail.client_id and gmail.client_secret to "
            "config/api_keys.json (Google Cloud OAuth Desktop client + Gmail API), "
            f"redirect URI {DEFAULT_REDIRECT}, then run "
            "python actions/gmail_bridge_client.py --login"
        )
    token = get_access_token(interactive=interactive)
    if token:
        return True, "Gmail API ready."
    return False, (
        "AUTH_REQUIRED: Gmail not linked. "
        "Run python actions/gmail_bridge_client.py --login "
        "or allow the browser login when prompted."
    )


def _build_raw_message(
    *, to: str, subject: str, body: str, extra_headers: dict[str, str] | None = None
) -> str:
    raw_recipients = (to or "").strip()
    if not raw_recipients or any(char in raw_recipients for char in "\r\n"):
        raise ValueError("A valid recipient email address is required.")
    recipients = getaddresses([raw_recipients])
    if not recipients or any(
        not address or not re.fullmatch(r"[^@\s<>]+@[^@\s<>]+\.[^@\s<>]+", address)
        for _name, address in recipients
    ):
        raise ValueError(f"Invalid recipient email address: {to}")

    msg = MIMEText(body or "", _charset="utf-8")
    msg["To"] = ", ".join(address for _name, address in recipients)
    msg["Subject"] = subject or "(no subject)"
    for header, value in (extra_headers or {}).items():
        if header.lower() not in {"to", "subject", "bcc", "cc"}:
            msg[header] = value
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("ascii")
    return raw


def send_email(*, to: str, subject: str, body: str) -> dict[str, Any]:
    ok, msg = ensure_linked(interactive=True)
    if not ok:
        return {"ok": False, "error": msg}
    token = get_access_token(interactive=False)
    if not token:
        return {"ok": False, "error": "AUTH_REQUIRED: Could not get Gmail access token."}

    try:
        raw = _build_raw_message(to=to, subject=subject, body=body)
    except ValueError as exc:
        return {"ok": False, "error": str(exc)}
    try:
        r = requests.post(
            GMAIL_SEND_URL,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            json={"raw": raw},
            timeout=30,
        )
    except Exception as e:
        return {"ok": False, "error": str(e)}

    if r.status_code == 401:
        # One refresh retry
        token2 = _refresh_access_token()
        if token2:
            r = requests.post(
                GMAIL_SEND_URL,
                headers={
                    "Authorization": f"Bearer {token2}",
                    "Content-Type": "application/json",
                },
                json={"raw": raw},
                timeout=30,
            )

    if r.status_code not in (200, 201):
        err = r.text[:300]
        try:
            err = r.json().get("error", {}).get("message") or err
        except Exception:
            pass
        if r.status_code in (401, 403):
            return {
                "ok": False,
                "error": f"AUTH_REQUIRED: Gmail API rejected send ({r.status_code}): {err}",
            }
        return {"ok": False, "error": f"Gmail send failed ({r.status_code}): {err}"}

    data = {}
    try:
        data = r.json()
    except Exception:
        pass
    return {"ok": True, "id": data.get("id"), "threadId": data.get("threadId")}


def auto_reply_gmail(
    *, message_id: str, recipient_email: str, reply_text: str
) -> dict[str, Any]:
    """Send a threaded Gmail reply to an existing message."""
    if not message_id or not recipient_email or not reply_text.strip():
        return {"ok": False, "error": "message_id, recipient_email, and reply_text are required."}
    ok, message = ensure_linked(interactive=True)
    if not ok:
        return {"ok": False, "error": message}
    token = get_access_token(interactive=False)
    if not token:
        return {"ok": False, "error": "AUTH_REQUIRED: Could not get Gmail access token."}

    headers = {"Authorization": f"Bearer {token}"}
    try:
        source = requests.get(
            f"{GMAIL_MESSAGES_URL}/{message_id}",
            headers=headers,
            params={
                "format": "metadata",
                "metadataHeaders": ["Message-ID", "References", "Subject"],
            },
            timeout=20,
        )
        if source.status_code != 200:
            return {"ok": False, "error": f"Gmail message lookup failed ({source.status_code})."}
        metadata = source.json()
        source_headers = {
            str(item.get("name") or "").lower(): str(item.get("value") or "")
            for item in ((metadata.get("payload") or {}).get("headers") or [])
        }
        message_ref = source_headers.get("message-id")
        if not message_ref:
            return {"ok": False, "error": "The Gmail message has no Message-ID header."}
        references = " ".join(
            value for value in (source_headers.get("references"), message_ref) if value
        )
        subject = source_headers.get("subject") or "(no subject)"
        if not subject.lower().startswith("re:"):
            subject = f"Re: {subject}"
        raw = _build_raw_message(
            to=recipient_email,
            subject=subject,
            body=reply_text,
            extra_headers={"In-Reply-To": message_ref, "References": references},
        )
        sent = requests.post(
            GMAIL_SEND_URL,
            headers={**headers, "Content-Type": "application/json"},
            json={"raw": raw, "threadId": metadata.get("threadId")},
            timeout=30,
        )
        data = sent.json() if sent.content else {}
        if not sent.ok:
            return {"ok": False, "error": data.get("error", {}).get("message") or sent.text[:300]}
        return {"ok": True, "id": data.get("id"), "threadId": data.get("threadId")}
    except ValueError as exc:
        return {"ok": False, "error": str(exc)}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def set_gmail_vacation_responder(
    *, enabled: bool, response_subject: str = "Out of office", response_body: str = "",
    restrict_to_contacts: bool = False, restrict_to_domain: bool = False,
) -> dict[str, Any]:
    """Enable or disable Gmail's global Vacation Responder."""
    if enabled and not response_body.strip():
        return {"ok": False, "error": "response_body is required when enabling the vacation responder."}
    ok, message = ensure_linked(interactive=True)
    if not ok:
        return {"ok": False, "error": message}
    token = get_access_token(interactive=False)
    if not token:
        return {"ok": False, "error": "AUTH_REQUIRED: Could not get Gmail access token."}
    payload = {
        "enableAutoReply": bool(enabled),
        "responseSubject": response_subject.strip() or "Out of office",
        "responseBodyPlainText": response_body,
        "restrictToContacts": bool(restrict_to_contacts),
        "restrictToDomain": bool(restrict_to_domain),
    }
    try:
        response = requests.put(
            GMAIL_VACATION_URL,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=30,
        )
        data = response.json() if response.content else {}
        if response.status_code == 401:
            return {"ok": False, "error": "AUTH_REQUIRED: Gmail session expired; sign in again."}
        if not response.ok:
            error = data.get("error", {}).get("message") or response.text[:300]
            if response.status_code == 403:
                error = (
                    f"Gmail settings permission is missing: {error}. "
                    "Run Gmail login again to grant gmail.settings.basic."
                )
            return {"ok": False, "error": error}
        return {"ok": True, "enabled": bool(enabled), "message": "Gmail Vacation Responder updated."}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def _after_timestamp(value: str | int | float | None) -> int | None:
    """Convert common spoken/tool time forms to a Gmail Unix-timestamp query."""
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        number = int(float(raw))
        return number if number > 100000000 else None
    except ValueError:
        pass
    from datetime import datetime
    now = datetime.now().astimezone()
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=now.tzinfo)
        return int(parsed.timestamp())
    except ValueError:
        pass
    import re
    match = re.search(r"\b(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\b", raw.lower())
    if match:
        hour = int(match.group(1))
        minute = int(match.group(2) or 0)
        meridiem = match.group(3)
        if meridiem == "pm" and hour < 12:
            hour += 12
        elif meridiem == "am" and hour == 12:
            hour = 0
        return int(now.replace(hour=hour, minute=minute, second=0, microsecond=0).timestamp())
    return None


def read_emails(*, after: str | int | float | None = None, limit: int = 20) -> dict[str, Any]:
    """Return recent Gmail message metadata/snippets, optionally after a time."""
    ok, msg = ensure_linked(interactive=True)
    if not ok:
        return {"ok": False, "error": msg}
    token = get_access_token(interactive=False)
    if not token:
        return {"ok": False, "error": "AUTH_REQUIRED: Gmail access token unavailable."}

    params: dict[str, Any] = {"maxResults": max(1, min(int(limit or 20), 50))}
    stamp = _after_timestamp(after)
    if stamp:
        params["q"] = f"after:{stamp}"
    headers = {"Authorization": f"Bearer {token}"}
    try:
        response = requests.get(GMAIL_MESSAGES_URL, headers=headers, params=params, timeout=30)
        if response.status_code == 401:
            token = _refresh_access_token()
            if token:
                headers["Authorization"] = f"Bearer {token}"
                response = requests.get(GMAIL_MESSAGES_URL, headers=headers, params=params, timeout=30)
        if response.status_code != 200:
            return {"ok": False, "error": f"Gmail read failed ({response.status_code}): {response.text[:240]}"}
        rows = []
        for item in (response.json().get("messages") or []):
            mid = item.get("id")
            if not mid:
                continue
            detail = requests.get(
                f"{GMAIL_MESSAGES_URL}/{mid}",
                headers=headers,
                params={"format": "metadata", "metadataHeaders": ["From", "Subject", "Date"]},
                timeout=20,
            )
            if detail.status_code != 200:
                continue
            payload = detail.json()
            headers_by_name = {
                str(h.get("name", "")).lower(): str(h.get("value", ""))
                for h in ((payload.get("payload") or {}).get("headers") or [])
            }
            rows.append({
                "from": headers_by_name.get("from", ""),
                "subject": headers_by_name.get("subject", "(no subject)"),
                "date": headers_by_name.get("date", ""),
                "snippet": str(payload.get("snippet") or "").strip(),
            })
        return {"ok": True, "count": len(rows), "after": after or "", "messages": rows}
    except Exception as exc:
        return {"ok": False, "error": f"Gmail read failed: {exc}"}


if __name__ == "__main__":
    if "--login" in sys.argv:
        try:
            print(run_oauth_flow(timeout=180.0, open_browser=True))
        except Exception as e:
            print(f"Login failed: {e}")
            sys.exit(1)
    elif "--status" in sys.argv:
        print(json.dumps(status(), indent=2))
    else:
        print("Usage: python actions/gmail_bridge_client.py --login | --status")
