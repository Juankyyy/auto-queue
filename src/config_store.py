"""
config_store.py — Persistencia validada de ajustes (config.json).
"""

import json
from typing import Any

from paths import atomic_write_json

CONFIG_DEFAULTS: dict[str, Any] = {
    "delay": 0.5,
    "threshold": 0.80,
    "auto_deactivate": True,
    "close_to_tray": True,
    "log_visible": True,
    "pos": None,
}

DELAY_MIN, DELAY_MAX = 0.1, 3.0
THRESHOLD_MIN, THRESHOLD_MAX = 0.50, 0.99


def load_config(path: str) -> dict[str, Any]:
    """Lee config.json con valores validados; defaults si falta o es inválido."""
    cfg: dict[str, Any] = dict(CONFIG_DEFAULTS)
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            cfg["delay"] = min(DELAY_MAX, max(DELAY_MIN,
                               float(data.get("delay", cfg["delay"]))))
            cfg["threshold"] = min(THRESHOLD_MAX, max(THRESHOLD_MIN,
                                    float(data.get("threshold", cfg["threshold"]))))
            cfg["auto_deactivate"] = bool(data.get("auto_deactivate",
                                           cfg["auto_deactivate"]))
            cfg["close_to_tray"] = bool(data.get("close_to_tray",
                                          cfg["close_to_tray"]))
            cfg["log_visible"] = bool(data.get("log_visible", cfg["log_visible"]))
            _pos = data.get("pos", None)
            if (isinstance(_pos, (list, tuple)) and len(_pos) == 2
                    and all(isinstance(v, (int, float)) for v in _pos)):
                cfg["pos"] = [int(_pos[0]), int(_pos[1])]
    except Exception:
        pass
    return cfg


def save_config(path: str, *, delay: float, threshold: float,
                auto_deactivate: bool, close_to_tray: bool,
                log_visible: bool, pos=None) -> None:
    """Guarda los ajustes actuales en config.json (escritura atómica)."""
    data = {
        "delay": round(float(delay), 2),
        "threshold": round(float(threshold), 2),
        "auto_deactivate": bool(auto_deactivate),
        "close_to_tray": bool(close_to_tray),
        "log_visible": bool(log_visible),
        "pos": ([int(pos[0]), int(pos[1])] if (
            isinstance(pos, (list, tuple)) and len(pos) == 2
            and all(isinstance(v, (int, float)) for v in pos))
            else None),
    }
    atomic_write_json(path, data)
