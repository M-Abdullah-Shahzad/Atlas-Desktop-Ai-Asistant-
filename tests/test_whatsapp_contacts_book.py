import actions.whatsapp_contacts_book as w


def test_lookup_exact_names_do_not_crash_fuzzy_fallback(monkeypatch):
    rows = [
        {
            "name": "Ahmad Munir",
            "aliases": ["Ahmad Munir", "Ahmad"],
            "phones": [{"raw": "03001234567", "prefer": True}],
        },
        {
            "name": "Ahmed Munir",
            "aliases": ["Ahmed Munir", "Ahmed"],
            "phones": [{"raw": "03009999999", "prefer": True}],
        },
    ]

    monkeypatch.setattr(w, "_load_rows", lambda: rows)
    monkeypatch.setattr(w, "_default_country_code", lambda: "92")

    ahmad = w.lookup("Ahmad Munir")
    ahmed = w.lookup("Ahmed Munir")

    assert ahmad is not None and ahmad["ok"] is True and ahmad["name"] == "Ahmad Munir"
    assert ahmed is not None and ahmed["ok"] is True and ahmed["name"] == "Ahmed Munir"
