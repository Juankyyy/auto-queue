"""Tests de bot.py: matching multi-escala, niveles y loop (sin display).

No mueve el mouse: _click se mockea y el failsafe se simula.
"""

import threading
import time

import cv2
import numpy as np
import pyautogui

import bot as botmod
from bot import LoLAutoAccept

RNG = np.random.RandomState(7)
BUTTON = (RNG.rand(40, 100, 3) * 255).astype(np.uint8)


def _shot_with(button, at):
    shot = np.zeros((400, 600, 3), dtype=np.uint8)
    h, w = button.shape[:2]
    y, x = at
    shot[y:y + h, x:x + w] = button
    return shot


def _templates():
    gray = cv2.cvtColor(BUTTON, cv2.COLOR_BGR2GRAY)
    out = []
    for s in LoLAutoAccept.TEMPLATE_SCALES:
        w = max(8, int(gray.shape[1] * s))
        h = max(8, int(gray.shape[0] * s))
        out.append((s, cv2.resize(gray, (w, h), interpolation=cv2.INTER_AREA)))
    return out


def _quiet(*args, **kwargs):
    return LoLAutoAccept(log_callback=lambda m, t="info": None)


def test_match_scale_1():
    b = _quiet()
    b.threshold = 0.8
    found, loc = b._match_template(_shot_with(BUTTON, (150, 250)), _templates())
    assert found
    assert abs(loc[0] - 300) <= 2 and abs(loc[1] - 170) <= 2


def test_match_scaled_button():
    b = _quiet()
    b.threshold = 0.8
    big = cv2.resize(BUTTON, (118, 47), interpolation=cv2.INTER_LINEAR)
    found, loc = b._match_template(_shot_with(big, (100, 100)), _templates())
    assert found
    assert abs(loc[0] - 159) <= 3 and abs(loc[1] - 123) <= 3


def test_no_false_positive_high_threshold():
    b = _quiet()
    b.threshold = 0.99
    noise = (RNG.rand(400, 600, 3) * 255).astype(np.uint8)
    assert b._match_template(noise, _templates()) == (False, None)


def test_compat_single_template_and_none():
    b = _quiet()
    b.threshold = 0.8
    found, loc = b._match_template(_shot_with(BUTTON, (150, 250)), BUTTON)
    assert found and abs(loc[0] - 300) <= 2
    assert b._match_template(_shot_with(BUTTON, (150, 250)), None) == (False, None)


def test_emit_supports_one_and_two_arg_callbacks():
    got1 = []
    botmod.LoLAutoAccept(log_callback=lambda m: got1.append(m))._emit("x", "warn")
    assert got1 == ["x"]
    got2 = []
    botmod.LoLAutoAccept(
        log_callback=lambda m, t="info": got2.append((m, t)))._emit("y", "error")
    assert got2 == [("y", "error")]


def test_default_callback_accepts_level():
    b = LoLAutoAccept()
    b.on_accepted(True)
    b.on_accepted(False)


def test_loop_accepts_and_clicks_center():
    real = cv2.imread(botmod._resolve_template_path(), cv2.IMREAD_COLOR)
    assert real is not None
    th, tw = real.shape[:2]
    canvas = np.zeros((th + 200, tw + 200, 3), dtype=np.uint8)
    oy, ox = 50, 60
    canvas[oy:oy + th, ox:ox + tw] = real
    calls, clicked = [], []
    b = LoLAutoAccept(log_callback=lambda m, t="info": None,
                      accepted_callback=lambda auto: calls.append(auto))
    b.delay = 0.01
    b.poll_interval = 0.01
    b._capture_screen = lambda bbox=None: canvas
    b._click = lambda loc: clicked.append(loc)
    th_run = threading.Thread(target=b.start, daemon=True)
    th_run.start()
    th_run.join(timeout=10)
    assert calls == [True]
    assert b.partidas_aceptadas == 1
    assert abs(clicked[0][0] - (ox + tw // 2)) <= 2
    assert abs(clicked[0][1] - (oy + th // 2)) <= 2


def test_stop_during_delay_does_not_click():
    b = _quiet()
    b.delay = 2.0
    b.poll_interval = 0.05
    b._load_template = lambda: "tpl"
    b._capture_screen = lambda bbox=None: "shot"
    b._match_template = lambda s, t: (True, (10, 10))
    clicked = []
    b._click = lambda loc: clicked.append(loc)
    th_run = threading.Thread(target=b.start, daemon=True)
    th_run.start()
    time.sleep(0.3)
    t0 = time.monotonic()
    b.stop()
    th_run.join(timeout=5)
    assert clicked == []
    assert time.monotonic() - t0 < 1.0
    assert not th_run.is_alive()


def test_failsafe_stops_loop():
    b = _quiet()
    b.delay = 0.01
    b.poll_interval = 0.01
    b._load_template = lambda: "tpl"
    b._capture_screen = lambda bbox=None: "shot"
    b._match_template = lambda s, t: (True, (10, 10))

    def _boom(loc):
        raise pyautogui.FailSafeException("test")

    b._click = _boom
    th_run = threading.Thread(target=b.start, daemon=True)
    th_run.start()
    th_run.join(timeout=5)
    assert not th_run.is_alive()
    assert b.running is False
