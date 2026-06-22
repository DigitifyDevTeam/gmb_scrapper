from app.utils.phone import (
    extract_phone_from_data_item_id,
    format_phone_display,
    normalize_phone,
)


def test_extract_phone_from_data_item_id() -> None:
    assert extract_phone_from_data_item_id("phone:tel:+33412345678") == "+33412345678"
    assert extract_phone_from_data_item_id("phone:tel:04 12 34 56 78") == "04 12 34 56 78"
    assert extract_phone_from_data_item_id("address:123") is None


def test_normalize_phone_france() -> None:
    assert normalize_phone("04 12 34 56 78", "france") == "+33412345678"


def test_format_phone_display_france() -> None:
    assert format_phone_display("+33412345678", "france") == "+33 4 12 34 56 78"
