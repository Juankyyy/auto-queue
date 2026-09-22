"""Tests de config_store.py (sin display)."""

import json

from config_store import load_config, save_config


def test_defaults_missing(tmp_path):
    cfg = load_config(str(tmp_path / "cfg.json"))
    assert cfg == {"delay": 0.5, "threshold": 0.8, "auto_deactivate": True,
                   "close_to_tray": True, "log_visible": True, "pos": None,
                   "lang": "en"}


def test_roundtrip_rounding(tmp_path):
    p = str(tmp_path / "cfg.json")
    save_config(p, delay=1.234, threshold=0.777, auto_deactivate=False,
                close_to_tray=True, log_visible=False, pos=[10, 20], lang="es")
    cfg = load_config(p)
    assert cfg["delay"] == 1.23
    assert cfg["threshold"] == 0.78
    assert cfg["auto_deactivate"] is False
    assert cfg["pos"] == [10, 20]
    assert cfg["lang"] == "es"


def test_lang_invalid_falls_back(tmp_path):
    p = str(tmp_path / "cfg.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump({"lang": "fr"}, f)
    assert load_config(p)["lang"] == "en"


def test_corrupt_falls_back_to_defaults(tmp_path):
    p = str(tmp_path / "cfg.json")
    open(p, "w", encoding="utf-8").write("{mal json")
    assert load_config(p)["delay"] == 0.5


def test_clamps(tmp_path):
    p = str(tmp_path / "cfg.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump({"delay": 99, "threshold": -5, "pos": [1]}, f)
    cfg = load_config(p)
    assert cfg["delay"] == 3.0
    assert cfg["threshold"] == 0.5
    assert cfg["pos"] is None
