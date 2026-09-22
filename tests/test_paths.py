"""Tests de paths.py (sin display)."""

import json
import os

from paths import atomic_write_json, bundled_path, migrate_user_file, user_data_dir


def test_bundled_path_dev():
    assert bundled_path("version.txt").endswith("version.txt")
    assert os.path.exists(bundled_path("version.txt"))


def test_user_data_dir_dev(tmp_path, monkeypatch):
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    monkeypatch.setenv("HOME", str(tmp_path))
    # Apunta a ~/Documents/LoL Auto Queue y la crea
    expected = os.path.join(str(tmp_path), "Documents", "LoL Auto Queue")
    assert user_data_dir() == expected
    assert os.path.isdir(expected)


def test_migrate_user_file_copies_legacy(tmp_path, monkeypatch):
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    monkeypatch.setenv("HOME", str(tmp_path))
    legacy = tmp_path / "legacy"
    legacy.mkdir()
    (legacy / "config.json").write_text('{"a": 1}', encoding="utf-8")
    monkeypatch.setattr("paths._legacy_data_dirs", lambda: [str(legacy)])
    dest = migrate_user_file("config.json")
    assert dest == os.path.join(user_data_dir(), "config.json")
    assert open(dest, encoding="utf-8").read() == '{"a": 1}'
    # No pisa un destino existente
    with open(dest, "w", encoding="utf-8") as f:
        f.write('{"b": 2}')
    migrate_user_file("config.json")
    assert open(dest, encoding="utf-8").read() == '{"b": 2}'


def test_atomic_write_json_no_tmp_left(tmp_path):
    p = str(tmp_path / "cfg.json")
    atomic_write_json(p, {"a": 1})
    assert json.load(open(p, encoding="utf-8")) == {"a": 1}
    assert not os.path.exists(p + ".tmp")
    atomic_write_json(p, {"b": [1, 2]})
    assert json.load(open(p, encoding="utf-8"))["b"] == [1, 2]
