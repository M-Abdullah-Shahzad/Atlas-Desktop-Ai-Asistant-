import json

import config


def test_get_config_requires_object_root(tmp_path, monkeypatch):
    config_file = tmp_path / "api_keys.json"
    monkeypatch.setattr(config, "_config_path", lambda: config_file)

    config_file.write_text(json.dumps(["invalid root"]), encoding="utf-8")
    assert config.get_config() == {}
    assert config.get_os() in {"windows", "mac", "linux"}

    config_file.write_text(json.dumps({"os_system": "windows"}), encoding="utf-8")
    assert config.get_config() == {"os_system": "windows"}
    assert config.get_os() == "windows"
