from actions import whatsapp_contacts_book as contacts


def test_malformed_phone_rows_are_ignored():
    assert contacts._pick_phone(
        [None, "not-a-phone-row", {"raw": "03001234567", "prefer": True}],
        "92",
    ) == "923001234567"
