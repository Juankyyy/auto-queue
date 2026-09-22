"""Tests de stats_store.py (sin display)."""

from datetime import datetime

from stats_store import MAX_STATS_EVENTS, StatsStore


def _sample(store):
    store.data = {
        "activations": ["2026-09-20T10:00:00"],
        "matches": ["2026-09-20T10:05:00"],
        "sessions": [{"start": "2026-09-20T10:00:00",
                      "end": "2026-09-20T10:10:00", "seconds": 600.0}],
    }
    return store


def test_aggregation_day(tmp_path):
    s = _sample(StatsStore(str(tmp_path / "s.json")))
    r = s.stats_for("day", now=datetime(2026, 9, 20, 12, 0, 0))
    assert (r["activations"], r["matches"], r["sessions"]) == (1, 1, 1)
    assert abs(r["seconds"] - 600.0) < 0.01
    assert "September" in r["label"]


def test_label_spanish(tmp_path):
    import i18n
    i18n.set_language("es")
    try:
        s = _sample(StatsStore(str(tmp_path / "s.json")))
        r = s.stats_for("day", now=datetime(2026, 9, 20, 12, 0, 0))
        assert "septiembre" in r["label"]
    finally:
        i18n.set_language("en")


def test_live_session_added(tmp_path):
    s = _sample(StatsStore(str(tmp_path / "s.json")))
    now = datetime(2026, 9, 20, 12, 0, 0)
    r = s.stats_for("day", now=now,
                    live_start=datetime(2026, 9, 20, 11, 0, 0))
    assert r["live"] == 3600.0
    assert abs(r["seconds"] - 4200.0) < 0.01


def test_ref_navigation(tmp_path):
    s = _sample(StatsStore(str(tmp_path / "s.json")))
    r = s.stats_for("day", ref=datetime(2026, 9, 19, 12, 0, 0),
                    now=datetime(2026, 9, 20, 12, 0, 0))
    assert (r["activations"], r["matches"]) == (0, 0)
    assert "19" in r["label"]


def test_fmt_duration():
    assert StatsStore.fmt_duration(3720) == "1 h 2 min"
    assert StatsStore.fmt_duration(90) == "1 min 30 s"
    assert StatsStore.fmt_duration(5) == "5 s"
    assert StatsStore.parse_ts("no-fecha") is None


def test_prune_and_reset(tmp_path):
    s = StatsStore(str(tmp_path / "s.json"))
    s.data["activations"] = list(range(MAX_STATS_EVENTS + 1000))
    s.prune()
    assert len(s.data["activations"]) == MAX_STATS_EVENTS
    s.reset()
    assert s.data == {"activations": [], "matches": [], "sessions": []}


def test_earliest(tmp_path):
    s = _sample(StatsStore(str(tmp_path / "s.json")))
    assert s.earliest() == datetime(2026, 9, 20, 10, 0, 0)
    assert StatsStore(str(tmp_path / "e.json")).earliest() is None
