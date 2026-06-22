import re


def normalize_address(address: str | None) -> str | None:
    if not address:
        return None

    cleaned = re.sub(r"\s+", " ", address.strip())
    return cleaned or None
