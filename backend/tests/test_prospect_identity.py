from app.utils.prospect_identity import (
    build_google_maps_profile_url,
    build_prospect_dedupe_key,
    canonical_maps_path,
    extract_maps_place_id,
    normalize_business_name,
    pick_best_maps_source_url,
)


def test_extract_maps_place_id_from_chij_url() -> None:
    url = "https://www.google.com/maps/place/Cafe/@48.8,2.3,17z/data=!3m1!4b1!4m6!3m5!1sChIJN1t_tDeuEmsRUsoyG83frY4"
    assert extract_maps_place_id(url) == "ChIJN1t_tDeuEmsRUsoyG83frY4"


def test_extract_maps_place_id_from_hex_token() -> None:
    url = (
        "https://www.google.com/maps/place/Test/data=!4m7!3m6!1s0x47e66e2964e34e2d"
        ":0x8ddca9ee380ef7ae!8m2!3d48.85!4d2.35"
    )
    assert extract_maps_place_id(url) == "0x47e66e2964e34e2d:0x8ddca9ee380ef7ae"


def test_same_business_different_url_formats_share_place_dedupe_key() -> None:
    url_a = "https://www.google.com/maps/place/Cafe/data=!3m1!1s0xabc:0xdef"
    url_b = "https://www.google.com/maps/place/Other+Name/data=!3m1!1s0xabc:0xdef"

    key_a, place_a = build_prospect_dedupe_key(
        business_name="Cafe",
        address="1 rue de Paris",
        maps_url=url_a,
    )
    key_b, place_b = build_prospect_dedupe_key(
        business_name="Other Name",
        address="99 avenue Lyon",
        maps_url=url_b,
    )

    assert place_a == place_b
    assert key_a == key_b


def test_canonical_maps_path_strips_coordinates() -> None:
    url = "https://www.google.com/maps/place/Cafe+De+Flore/@48.854102,2.332600,17z"
    assert canonical_maps_path(url) == "/maps/place/cafe de flore"


def test_dedupe_key_falls_back_to_phone_without_maps_url() -> None:
    key, place_id = build_prospect_dedupe_key(
        business_name="Garage Martin",
        address=None,
        phone="06 12 34 56 78",
        maps_url=None,
        country="France",
    )

    assert place_id is None
    assert key.startswith("phone:")


def test_normalize_business_name_collapses_whitespace_and_case() -> None:
    assert normalize_business_name("  Cafe   Martin  ") == "cafe martin"


def test_dedupe_key_uses_name_and_address_when_no_maps_or_phone() -> None:
    key_a, _ = build_prospect_dedupe_key(
        business_name="Boulangerie",
        address="10 Rue Haute",
        maps_url=None,
        phone=None,
    )
    key_b, _ = build_prospect_dedupe_key(
        business_name="boulangerie",
        address="10 rue haute",
        maps_url=None,
        phone=None,
    )

    assert key_a == key_b


def test_pick_best_maps_source_url_prefers_card_href_with_place_id() -> None:
    card_href = (
        "https://www.google.com/maps/place/Boulangerie/data=!4m6!3m5!1s0xabc:0xdef"
    )
    stale_page_url = "https://www.google.com/maps/place/Wrong+Business/@48,2,17z"

    picked = pick_best_maps_source_url(card_href, stale_page_url)

    assert picked == card_href


def test_build_google_maps_profile_url_uses_place_id_for_chij() -> None:
    url = build_google_maps_profile_url(
        business_name="Cafe de Flore",
        address="172 Bd Saint-Germain, Paris",
        maps_place_id="ChIJN1t_tDeuEmsRUsoyG83frY4",
    )

    assert "query_place_id=ChIJN1t_tDeuEmsRUsoyG83frY4" in url
    assert "Cafe" in url


def test_build_google_maps_profile_url_falls_back_to_name_and_address() -> None:
    url = build_google_maps_profile_url(
        business_name="Plombier Dupont",
        address="12 rue Victor Hugo",
        city="Lyon",
        country="France",
        maps_url=None,
    )

    assert url is not None
    assert "maps/search" in url
    assert "Plombier" in url
    assert "12" in url
    assert "Lyon" in url
