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


APP_DIR_NAME = "LoL Auto Queue"


def _legacy_data_dirs() -> list:
    """Ubicaciones anteriores de config.json/stats.json (para migración)."""
    dirs = []
    try:
        dirs.append(_repo_root())
    except Exception:
        pass
    try:
        if getattr(sys, "frozen", False):
            # El .exe vive en dist/ dentro del proyecto: los datos legacy
            # están junto al exe o en la carpeta padre (raíz del proyecto).
            exe_dir = os.path.dirname(sys.executable)
            for d in (exe_dir, os.path.dirname(exe_dir)):
                if d and d not in dirs:
                    dirs.append(d)
    except Exception:
        pass
    return dirs


def user_data_dir() -> str:
    """Carpeta de datos del usuario: ~/Documents/LoL Auto Queue."""
    try:
        base = os.path.join(os.path.expanduser("~"), "Documents", APP_DIR_NAME)
        os.makedirs(base, exist_ok=True)
        return base
    except Exception:
        pass
    # Fallback: comportamiento anterior (junto al .exe si congelado, si no repo).
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return _repo_root()


def migrate_user_file(name: str, dest_name: str | None = None) -> str:
    """Copia un archivo desde ubicaciones legacy si no existe en user_data_dir.

    `name` es la ruta relativa en la ubicación legacy y `dest_name` (por
    defecto igual) la relativa en la carpeta del usuario. Devuelve la ruta
    destino. No sobrescribe nunca.
    """
    dest_rel = dest_name if dest_name is not None else name
    dest = os.path.join(user_data_dir(), dest_rel)
    if os.path.exists(dest):
        return dest
    try:
        current = os.path.dirname(dest)
        for old_dir in _legacy_data_dirs():
            if os.path.abspath(old_dir) == os.path.abspath(current):
                continue
            src = os.path.join(old_dir, name)
            if os.path.isfile(src):
                parent = os.path.dirname(dest)
                if parent:
                    os.makedirs(parent, exist_ok=True)
                import shutil
                shutil.copy2(src, dest)
                break
    except Exception:
        pass
    return dest


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
