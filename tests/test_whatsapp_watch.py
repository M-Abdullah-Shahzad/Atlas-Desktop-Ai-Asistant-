import json

import actions.whatsapp_watch as watch
import memory.config_manager as config_manager


def test_watch_config_handles_non_object_root(tmp_path, monkeypatch):
    config_file = tmp_path / "api_keys.json"
    monkeypatch.setattr(config_manager, "CONFIG_FILE", config_file)
    monkeypatch.setattr(watch, "_enabled_cache", None)

    config_file.write_text(json.dumps(["invalid root"]), encoding="utf-8")
    assert watch._user_name() == ""
    assert watch.is_auto_reply_enabled() is False
