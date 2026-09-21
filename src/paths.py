"""
paths.py — Rutas de recursos y escritura atómica de JSON.

Funciona tanto en `.py` (raiz del repo) como en el `.exe` de PyInstaller.
"""

import json
import os
import sys
from typing import Any

_ROOT_MARKER = "pyproject.toml"


def _repo_root() -> str:
    """Raiz del proyecto: sube desde este archivo hasta el marcador."""
    here = os.path.dirname(os.path.abspath(__file__))
    node = here
    for _ in range(5):
        if os.path.exists(os.path.join(node, _ROOT_MARKER)):
            return node
        parent = os.path.dirname(node)
        if parent == node:
            break
        node = parent
    return here


def bundled_path(*parts: str) -> str:
    """Ruta a un recurso empaquetado (assets, version.txt)."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, *parts)
    return os.path.join(_repo_root(), *parts)


def user_data_dir() -> str:
    """Carpeta escribible para config.json/stats.json (junto al .exe si congelado)."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return _repo_root()


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
