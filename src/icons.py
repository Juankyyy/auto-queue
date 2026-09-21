"""
icons.py — Fuente de iconos Font Awesome 6 Free (Solid).

Los glifos son monocromos y se tinan con `fg`, asi escalan nitidos a
cualquier tamano/DPI sin dependencias extra (carga privada via GDI).

Atribucion: Font Awesome Free 6.x por Fonticons, Inc. (CC BY 4.0).
https://fontawesome.com/license/free
"""

import ctypes
import os

from paths import bundled_path

FAMILY = "Font Awesome 6 Free Solid"
_FONT_FILE = ("assets", "fonts", "fa-solid-900.ttf")

# Codepoints PUA estables de Font Awesome 6 Free Solid.
GLYPHS = {
    "gear": "\uf013",    # ajustes
    "chart": "\uf201",   # estadisticas (chart-line)
    "house": "\uf015",   # inicio
    "note": "\uf249",    # registro (note-sticky)
    "xmark": "\uf00d",   # cerrar
}

_loaded = False


def load_icon_font() -> bool:
    """Registra la fuente en privado para este proceso. Idempotente."""
    global _loaded
    if _loaded:
        return True
    try:
        path = bundled_path(*_FONT_FILE)
        if not os.path.exists(path):
            return False
        buf = ctypes.create_unicode_buffer(path)
        added = ctypes.windll.gdi32.AddFontResourceExW(buf, 0x10, 0)
        _loaded = bool(added)
        return _loaded
    except Exception:
        return False


def family() -> str:
    """Familia a usar en widgets (carga la fuente si hace falta)."""
    load_icon_font()
    return FAMILY


def glyph(name: str) -> str | None:
    return GLYPHS.get(name)
