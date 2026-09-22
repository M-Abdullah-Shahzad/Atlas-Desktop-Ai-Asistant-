import actions.whatsapp_contacts_book as contacts


def test_normalize_phone_accepts_numeric_inputs_and_rejects_short_values():
    assert contacts.normalize_phone(3001234567, 92) == "923001234567"
    assert contacts.normalize_phone("03001234567", "pk-92") == "923001234567"
    assert contacts.normalize_phone("123", 92) == ""
