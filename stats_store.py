"""
stats_store.py — Persistencia y agregación de estadísticas de uso (stats.json).
"""

import calendar  # noqa: F401 (reservado para futura navegación por meses)
import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from paths import atomic_write_json

MAX_STATS_EVENTS = 5000


class StatsStore:
    """Carga, guarda (atómico + podado) y agrega eventos de uso."""

    MESES = ("enero", "febrero", "marzo", "abril", "mayo", "junio",
             "julio", "agosto", "septiembre", "octubre", "noviembre",
             "diciembre")

    def __init__(self, path: str) -> None:
        self._path = path
        self.data: Dict[str, List[Any]] = {
            "activations": [], "matches": [], "sessions": [],
        }

    # ── Persistencia ──

    def load(self) -> Dict[str, List[Any]]:
        """Lee stats.json; estructura válida o vacía si falta/es inválido."""
        stats: Dict[str, List[Any]] = {
            "activations": [], "matches": [], "sessions": [],
        }
        try:
            with open(self._path, "r", encoding="utf-8") as f:
                raw = json.load(f)
            if isinstance(raw, dict):
                for key in stats:
                    val = raw.get(key, [])
                    if isinstance(val, list):
                        stats[key] = val
        except Exception:
            pass
        self.data = stats
        return stats

    def save(self) -> None:
        """Guarda los eventos en stats.json (atómico + podado)."""
        try:
            self.prune()
            atomic_write_json(self._path, self.data)
        except Exception:
            pass

    def prune(self, limit: int = MAX_STATS_EVENTS) -> None:
        """Conserva solo los últimos N eventos por lista."""
        try:
            for key in ("activations", "matches", "sessions"):
                val = self.data.get(key)
                if isinstance(val, list) and len(val) > limit:
                    self.data[key] = val[-limit:]
        except Exception:
            pass

    def reset(self) -> None:
        """Vacía todos los eventos y persiste."""
        self.data = {"activations": [], "matches": [], "sessions": []}
        self.save()

    def earliest(self) -> Optional[datetime]:
        """Fecha/hora del evento más antiguo, o None si no hay datos."""
        best: Optional[datetime] = None
        try:
            for ts in self.data.get("activations", []):
                dt = self.parse_ts(ts)
                if dt is not None and (best is None or dt < best):
                    best = dt
            for ts in self.data.get("matches", []):
                dt = self.parse_ts(ts)
                if dt is not None and (best is None or dt < best):
                    best = dt
            for s in self.data.get("sessions", []):
                if isinstance(s, dict):
                    for key in ("start", "end"):
                        dt = self.parse_ts(s.get(key, ""))
                        if dt is not None and (best is None or dt < best):
                            best = dt
        except Exception:
            pass
        return best

    # ── Registro ──

    def record_activation(self, when: datetime) -> str:
        ts = when.isoformat()
        self.data["activations"].append(ts)
        return ts

    def record_match(self, when: datetime) -> str:
        ts = when.isoformat()
        self.data["matches"].append(ts)
        return ts

    def close_session(self, start: datetime, end: datetime) -> None:
        self.data["sessions"].append({
            "start": start.isoformat(),
            "end": end.isoformat(),
            "seconds": round((end - start).total_seconds(), 1),
        })

    # ── Agregación ──

    @staticmethod
    def parse_ts(value: Any) -> Optional[datetime]:
        try:
            return datetime.fromisoformat(value)
        except Exception:
            return None

    @classmethod
    def period_bounds(cls, period: str,
                      ref: Optional[datetime] = None
                      ) -> Tuple[datetime, datetime, str]:
        """(inicio, fin, etiqueta) del periodo calendario que contiene a ref."""
        ref = ref or datetime.now()
        if period == "week":
            start = datetime(ref.year, ref.month, ref.day) - timedelta(days=ref.weekday())
            end = start + timedelta(days=7)
            label = (f"{start.day} – {end.day - 1} "
                     f"{cls.MESES[start.month - 1]} {start.year}")
        elif period == "month":
            start = datetime(ref.year, ref.month, 1)
            end = datetime(ref.year + (ref.month == 12), ref.month % 12 + 1, 1)
            label = f"{cls.MESES[ref.month - 1]} {ref.year}"
        elif period == "year":
            start = datetime(ref.year, 1, 1)
            end = datetime(ref.year + 1, 1, 1)
            label = str(ref.year)
        else:  # day
            start = datetime(ref.year, ref.month, ref.day)
            end = start + timedelta(days=1)
            label = f"{start.day} {cls.MESES[start.month - 1]} {start.year}"
        return start, end, label

    def stats_for(self, period: str,
                  ref: Optional[datetime] = None,
                  live_start: Optional[datetime] = None,
                  now: Optional[datetime] = None) -> Dict[str, Any]:
        """Agrega eventos del periodo visible: partidas, activaciones y tiempo."""
        now = now or datetime.now()
        start, end, label = self.period_bounds(period, ref or now)
        matches = sum(1 for ts in self.data["matches"]
                      if (dt := self.parse_ts(ts)) is not None and start <= dt < end)
        activations = sum(1 for ts in self.data["activations"]
                          if (dt := self.parse_ts(ts)) is not None and start <= dt < end)
        seconds, sessions = 0.0, 0
        for s in self.data["sessions"]:
            s0 = self.parse_ts(s.get("start", ""))
            s1 = self.parse_ts(s.get("end", ""))
            if s0 is None or s1 is None:
                continue
            overlap = (min(s1, end) - max(s0, start)).total_seconds()
            if overlap > 0:
                seconds += overlap
                sessions += 1
        live = 0.0
        if live_start is not None:
            live = max(0.0, (min(now, end) - max(live_start, start)
                              ).total_seconds())
            seconds += live
        return {
            "label": label,
            "matches": matches,
            "activations": activations,
            "seconds": seconds,
            "sessions": sessions,
            "live": live,
            "avg_per_activation": (matches / activations) if activations else 0.0,
            "avg_session": (seconds / sessions) if sessions else 0.0,
        }

    @staticmethod
    def fmt_duration(seconds: float) -> str:
        """Formatea segundos como '2 h 15 min', '45 min 10 s' o '35 s'."""
        seconds = int(max(0, seconds))
        h, rem = divmod(seconds, 3600)
        m, s = divmod(rem, 60)
        if h:
            return f"{h} h {m} min" if m else f"{h} h"
        if m:
            return f"{m} min {s} s" if s else f"{m} min"
        return f"{s} s"
