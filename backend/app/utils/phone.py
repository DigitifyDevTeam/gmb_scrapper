import re

import phonenumbers
from phonenumbers import NumberParseException, PhoneNumberFormat

_PHONE_DATA_ITEM_PATTERN = re.compile(r"phone:tel:([^;]+)", re.IGNORECASE)


def extract_phone_from_data_item_id(data_item_id: str | None) -> str | None:
    if not data_item_id:
        return None
    match = _PHONE_DATA_ITEM_PATTERN.search(data_item_id)
    if not match:
        return None
    phone = match.group(1).strip()
    return phone or None


def format_phone_display(phone: str | None, country_code: str = "france") -> str | None:
    if not phone:
        return None

    region = _country_to_region(country_code)
    try:
        parsed = phonenumbers.parse(phone.strip(), region)
        if phonenumbers.is_valid_number(parsed):
            return phonenumbers.format_number(parsed, PhoneNumberFormat.INTERNATIONAL)
    except NumberParseException:
        pass
    return phone.strip()


def normalize_phone(phone: str | None, country_code: str) -> str | None:
    if not phone:
        return None

    cleaned = phone.strip()
    if not cleaned:
        return None

    region = _country_to_region(country_code)
    try:
        parsed = phonenumbers.parse(cleaned, region)
        if not phonenumbers.is_valid_number(parsed):
            return cleaned
        return phonenumbers.format_number(parsed, PhoneNumberFormat.E164)
    except NumberParseException:
        return cleaned


def _country_to_region(country: str) -> str:
    mapping = {
        "france": "FR",
        "fr": "FR",
        "united states": "US",
        "usa": "US",
        "us": "US",
        "united kingdom": "GB",
        "uk": "GB",
        "germany": "DE",
        "de": "DE",
        "spain": "ES",
        "es": "ES",
        "italy": "IT",
        "it": "IT",
        "canada": "CA",
        "ca": "CA",
        "morocco": "MA",
        "ma": "MA",
        "tunisia": "TN",
        "tn": "TN",
    }
    return mapping.get(country.strip().lower(), "FR")
