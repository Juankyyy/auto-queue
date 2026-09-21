"""Tests de paths.py (sin display)."""

import json
import os

from paths import atomic_write_json, bundled_path, user_data_dir


def test_bundled_path_dev():
    assert bundled_path("version.txt").endswith("version.txt")
    assert os.path.exists(bundled_path("version.txt"))


def test_user_data_dir_dev(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    # En dev (.py, no frozen) es la raiz del repo (marcador pyproject.toml)
    assert os.path.isdir(user_data_dir())


def test_atomic_write_json_no_tmp_left(tmp_path):
    p = str(tmp_path / "cfg.json")
    atomic_write_json(p, {"a": 1})
    assert json.load(open(p, encoding="utf-8")) == {"a": 1}
    assert not os.path.exists(p + ".tmp")
    atomic_write_json(p, {"b": [1, 2]})
    assert json.load(open(p, encoding="utf-8"))["b"] == [1, 2]
