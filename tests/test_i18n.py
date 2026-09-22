"""Tests de i18n.py (sin display)."""

from i18n import get_language, months, set_language, t


def test_default_is_english():
    set_language("en")
    assert get_language() == "en"
    assert t("start_bot") == "START BOT"


def test_spanish():
    set_language("es")
    try:
        assert t("start_bot") == "ACTIVAR BOT"
        assert t("status_idle") == "INACTIVO"
    finally:
        set_language("en")


def test_invalid_falls_back_to_english():
    set_language("xx")
    assert get_language() == "en"
    set_language(None)
    assert get_language() == "en"


def test_key_parity_between_languages():
    import i18n as mod
    assert set(mod._STRINGS["en"]) == set(mod._STRINGS["es"])


def test_format_placeholders():
    set_language("en")
    assert t("match_found", secs="1.23") == "✅ Match found! Accepting in 1.23s..."
    assert t("match_accepted", n=3) == "🎮 Match #3 accepted."
    set_language("es")
    try:
        assert t("match_found", secs="1.23") == "✅ ¡Partida encontrada! Aceptando en 1.23s..."
    finally:
        set_language("en")


def test_months():
    set_language("en")
    assert months()[8] == "September"
    set_language("es")
    try:
        assert months()[8] == "septiembre"
    finally:
        set_language("en")
    assert len(months()) == 12
