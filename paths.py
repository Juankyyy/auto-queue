"""
paths.py — Rutas de recursos y escritura atómica de JSON.

Funciona tanto en `.py` como en el `.exe` generado por PyInstaller.
"""

import json
import os
import sys
from typing import Any


def bundled_path(*parts: str) -> str:
    """Ruta a un recurso empaquetado (templates, iconos, version.txt)."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, *parts)
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), *parts)


def user_data_dir() -> str:
    """Carpeta escribible para config.json/stats.json (junto al .exe si congelado)."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def atomic_write_json(path: str, data: Any) -> None:
    """Escritura atómica: tmp + fsync + os.replace para no corromper en cortes."""
    tmp = f"{path}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
        f.flush()
        try:
            os.fsync(f.fileno())
        except Exception:
            pass
    os.replace(tmp, path)
