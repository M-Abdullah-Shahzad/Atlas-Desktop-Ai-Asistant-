import json

import dashboard.server as dashboard_server
import memory.config_manager as config_manager


def test_dashboard_key_loader_handles_non_object_root(tmp_path, monkeypatch):
    config_file = tmp_path / "api_keys.json"
    monkeypatch.setattr(config_manager, "CONFIG_FILE", config_file)
    config_dir = tmp_path / "config"
    config_dir.mkdir()

    config_file.write_text(json.dumps(["invalid root"]), encoding="utf-8")
    assert dashboard_server._get_gemini_key() is None

    config_file.write_text(json.dumps({"gemini_api_key": "test-key"}), encoding="utf-8")
    assert dashboard_server._get_gemini_key() == "test-key"
