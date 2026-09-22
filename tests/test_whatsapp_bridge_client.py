import actions.whatsapp_bridge_client as bridge
import actions.whatsapp_control as control
from core.agent_orchestrator import AgentOrchestrator


class _Response:
    def __init__(self, data, ok=True):
        self._data = data
        self.ok = ok
        self.content = b"{}"
        self.text = ""

    def json(self):
        return self._data


def test_cache_rows_require_a_trusted_name(monkeypatch):
    monkeypatch.setattr(bridge.contacts_book, "display_for_jid", lambda jid, fallback="": "")

    assert not bridge._cache_row_is_valid(
        "Ahmad Munir",
        {"jid": "923001234567@s.whatsapp.net", "name": ""},
    )
    assert not bridge._cache_row_is_valid(
        "Ahmad Munir",
        {"jid": "923001234567@s.whatsapp.net", "name": "Ahmed Munir"},
    )
    assert bridge._cache_row_is_valid(
        "Ahmad Munir",
        {"jid": "923001234567@s.whatsapp.net", "name": "Ahmad Munir"},
    )


def test_send_requires_bridge_message_confirmation(monkeypatch):
    monkeypatch.setattr(bridge, "ensure_bridge", lambda: (True, ""))
    monkeypatch.setattr(bridge, "status", lambda: {"state": "connected"})
    monkeypatch.setattr(bridge, "_http", lambda *args, **kwargs: _Response({"ok": True, "sent": True}))

    result = bridge.send("123@s.whatsapp.net", "hello")

    assert result["ok"] is False
    assert result["sent"] is False
    assert "message" in result["error"]


def test_send_returns_proof_when_bridge_confirms(monkeypatch):
    monkeypatch.setattr(bridge, "ensure_bridge", lambda: (True, ""))
    monkeypatch.setattr(bridge, "status", lambda: {"state": "connected"})
    monkeypatch.setattr(
        bridge,
        "_http",
        lambda *args, **kwargs: _Response({"ok": True, "sent": True, "messageId": "msg-1", "jid": "123@s.whatsapp.net"}),
    )

    result = bridge.send("123@s.whatsapp.net", "hello")

    assert result == {"ok": True, "sent": True, "messageId": "msg-1", "jid": "123@s.whatsapp.net"}


def test_whatsapp_topic_expands_in_roman_urdu():
    message = control.expand_topic_roman_urdu("ask for project update", "Ali")

    assert message.startswith("Assalam o Alaikum Ali")
    assert "project ki current progress" in message
    assert "please" not in message.lower()


def test_whatsapp_numeric_contact_is_rejected_without_manual_number_prompt(monkeypatch):
    monkeypatch.setattr(control.bridge, "resolve", lambda *args, **kwargs: {
        "ok": False,
        "status": "NOT_FOUND",
        "type": "contact",
        "query": "+923001234567",
    })
    error, jid, label, is_group = control._resolve_contact("+923001234567")

    assert error and "not found" in error.lower()
    assert (jid, label, is_group) == ("", "", False)


def test_resolve_preserves_not_found_status(monkeypatch):
    monkeypatch.setattr(bridge, "ensure_bridge", lambda: (True, ""))
    monkeypatch.setattr(bridge, "status", lambda: {"state": "connected"})
    monkeypatch.setattr(
        bridge,
        "_http",
        lambda *args, **kwargs: _Response(
            {"ok": False, "status": "NOT_FOUND", "type": "contact", "query": "Ahmad Munir"},
            ok=False,
        ),
    )

    result = bridge.resolve("Ahmad Munir", kind="contact")

    assert result["status"] == "NOT_FOUND"
    assert result["type"] == "contact"
    assert result["query"] == "Ahmad Munir"


def test_resolve_preserves_ambiguous_matches(monkeypatch):
    monkeypatch.setattr(bridge, "ensure_bridge", lambda: (True, ""))
    monkeypatch.setattr(bridge, "status", lambda: {"state": "connected"})
    monkeypatch.setattr(
        bridge,
        "_http",
        lambda *args, **kwargs: _Response(
            {
                "ok": False,
                "status": "AMBIGUOUS",
                "type": "contact",
                "query": "Ahmad Munir",
                "matches": [{"jid": "1@s.whatsapp.net", "display_name": "Ahmad Munir"}],
            },
            ok=False,
        ),
    )

    result = bridge.resolve("Ahmad Munir", kind="contact")

    assert result["status"] == "AMBIGUOUS"
    assert result["matches"][0]["display_name"] == "Ahmad Munir"


def test_resolve_accepts_only_verified_whatsapp_result(monkeypatch):
    monkeypatch.setattr(bridge, "ensure_bridge", lambda: (True, ""))
    monkeypatch.setattr(bridge, "status", lambda: {"state": "connected"})
    monkeypatch.setattr(
        bridge,
        "_http",
        lambda *args, **kwargs: _Response(
            {
                "ok": True,
                "status": "FOUND",
                "type": "contact",
                "jid": "923001234567@s.whatsapp.net",
                "display_name": "Ahmad Munir",
                "source": "whatsapp",
                "isGroup": False,
            }
        ),
    )

    result = bridge.resolve("Ahmad Munir", kind="contact")

    assert result == {
        "ok": True,
        "status": "FOUND",
        "type": "contact",
        "jid": "923001234567@s.whatsapp.net",
        "name": "Ahmad Munir",
        "display_name": "Ahmad Munir",
        "source": "whatsapp",
        "isGroup": False,
    }


def test_orchestrator_routes_topic_message(monkeypatch):
    captured = {}

    def fake_control(parameters, player=None):
        captured.update(parameters)
        return "Sent WhatsApp message to Ali."

    monkeypatch.setattr(control, "whatsapp_control", fake_control)
    result = AgentOrchestrator().send_whatsapp_topic("Ali", "ask for project update")

    assert result.startswith("Sent WhatsApp")
    assert captured == {"action": "message", "contact": "Ali", "topic": "ask for project update"}
