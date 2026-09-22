import json

import actions.spotify_control as spotify


def test_spotify_config_requires_object_root(tmp_path, monkeypatch):
    config_file = tmp_path / "api_keys.json"
    monkeypatch.setattr(spotify, "_config_path", lambda: config_file)

    config_file.write_text(json.dumps(["invalid root"]), encoding="utf-8")
    assert spotify._load_config() == {}


def test_invalid_spotify_expiry_does_not_raise(monkeypatch):
    monkeypatch.setattr(
        spotify,
        "_spotify_cfg",
        lambda: {"access_token": "token", "expires_at": "not-a-number"},
    )
    monkeypatch.setattr(spotify, "_refresh_access_token", lambda: None)

    assert spotify._get_access_token() == "token"


def test_manual_callback_completes_pending_pkce_login(monkeypatch):
    persisted = {}
    monkeypatch.setattr(
        spotify,
        "_exchange_code",
        lambda client_id, code, verifier, redirect_uri: {
            "access_token": "access",
            "refresh_token": "refresh",
            "expires_in": 3600,
        },
    )
    monkeypatch.setattr(
        spotify,
        "_persist_token_response",
        lambda payload: persisted.update(payload),
    )
    spotify._set_pending_oauth("client", "verifier", spotify.DEFAULT_REDIRECT, "state-123")

    result = spotify.complete_spotify_login(
        f"{spotify.DEFAULT_REDIRECT}?code=auth-code&state=state-123"
    )

    assert result.startswith("Spotify linked")
    assert persisted["access_token"] == "access"
    assert spotify._oauth_pending is None


def test_manual_callback_rejects_missing_code(monkeypatch):
    spotify._set_pending_oauth("client", "verifier", spotify.DEFAULT_REDIRECT, "state-123")

    try:
        spotify.complete_spotify_login(f"{spotify.DEFAULT_REDIRECT}?state=state-123")
    except RuntimeError as exc:
        assert "code=" in str(exc)
    else:
        raise AssertionError("Expected callback without code= to be rejected")
    finally:
        spotify._clear_pending_oauth()


def test_manual_callback_rejects_state_mismatch():
    spotify._set_pending_oauth("client", "verifier", spotify.DEFAULT_REDIRECT, "state-123")

    try:
        spotify.complete_spotify_login(
            f"{spotify.DEFAULT_REDIRECT}?code=auth-code&state=wrong-state"
        )
    except RuntimeError as exc:
        assert "state mismatch" in str(exc).lower()
    else:
        raise AssertionError("Expected callback with mismatched state to be rejected")
    finally:
        spotify._clear_pending_oauth()
