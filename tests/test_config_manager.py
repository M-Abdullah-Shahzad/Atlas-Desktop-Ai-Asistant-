import json

import memory.config_manager as config_manager


def test_load_api_keys_requires_object_root(tmp_path, monkeypatch):
    config_file = tmp_path / "api_keys.json"
    monkeypatch.setattr(config_manager, "CONFIG_FILE", config_file)

    config_file.write_text(json.dumps(["not", "a", "mapping"]), encoding="utf-8")
    assert config_manager.load_api_keys() == {}

    config_file.write_text(json.dumps({"assistant_name": "Atlas"}), encoding="utf-8")
    assert config_manager.load_api_keys() == {"assistant_name": "Atlas"}
