"""Tests de ScrollHost (requiere display; se omiten sin él)."""

import tkinter as tk
import types

import pytest

from main import ScrollHost


@pytest.fixture(scope="session")
def root():
    tk = pytest.importorskip("tkinter")
    try:
        r = tk.Tk()
    except tk.TclError:
        pytest.skip("sin display")
    try:
        r.geometry("+2000+2000")
        r.deiconify()
        r.update_idletasks()
    except Exception:
        pass
    yield r
    try:
        r.destroy()
    except Exception:
        pass


def _host(root, height=200, content_h=1000):
    host = ScrollHost(root, height=height)
    host.pack(fill="both", expand=True)
    filler = tk.Frame(host.inner, bg="#161B22", height=content_h)
    filler.pack(fill="x")
    root.update_idletasks()
    root.update()
    return host


@pytest.fixture()
def clean_hosts(root):
    yield
    for child in list(root.winfo_children()):
        try:
            child.destroy()
        except Exception:
            pass
    try:
        root.update_idletasks()
    except Exception:
        pass


def test_sin_barra_si_cabe_todo(root, clean_hosts):
    host = _host(root, height=400, content_h=50)
    assert host.bar.winfo_class() == "Canvas"
    assert not host.bar.winfo_ismapped()


def test_barra_visible_con_desborde(root, clean_hosts):
    host = _host(root, height=200, content_h=1000)
    # diferida: no aparece de inmediato...
    assert not host.bar.winfo_ismapped()
    host._show_now()
    root.update_idletasks()
    assert host.bar.winfo_ismapped()
    # flotante: el canvas conserva todo el ancho (sin corrimiento)
    assert host.canvas.winfo_width() == host.winfo_width()
    # la pastilla redondeada está arriba y ocupa 3 items persistentes
    assert len(host.bar.find_withtag("sthumb")) == 3
    _x0, y0, _x1, y1 = host.bar.bbox("sthumb")
    assert y0 <= 4
    assert y1 > y0


def test_rueda_hace_scroll(root, clean_hosts):
    host = _host(root, height=200, content_h=1000)
    assert host.canvas.yview()[0] == 0.0
    child = host.inner.winfo_children()[0]
    evt = types.SimpleNamespace(
        widget=child,
        x_root=child.winfo_rootx() + 5,
        y_root=child.winfo_rooty() + 5,
        delta=-120,
    )
    ScrollHost._route_wheel(evt)
    root.update_idletasks()
    assert host.canvas.yview()[0] > 0.0


def test_click_y_arrastre_en_thumb(root, clean_hosts):
    host = _host(root, height=200, content_h=1000)
    host._show_now()
    root.update_idletasks()
    _x0, y0, _x1, y1 = host.bar.bbox("sthumb")
    assert y0 <= 4
    host.bar.event_generate("<ButtonPress-1>", x=6, y=int(y0) + 2)
    root.update()
    host.bar.event_generate("<B1-Motion>", x=6, y=int(y0) + 120)
    root.update()
    host.bar.event_generate("<ButtonRelease-1>", x=6, y=int(y0) + 120)
    root.update()
    assert host.canvas.yview()[0] > 0.0
    assert host._drag_root is None


def test_squelch_retrasa_aparicion(root, clean_hosts):
    host = _host(root, height=200, content_h=1000)
    host.squelch(60000)
    host._on_scroll(0.0, 0.5)
    assert host._show_job is not None
    root.update_idletasks()
    root.update()
    assert not host.bar.winfo_ismapped()
    host._cancel_show()
    host._squelch_until = 0.0
    host._on_scroll(0.0, 0.5)
    host._show_now()
    root.update_idletasks()
    assert host.bar.winfo_ismapped()


def test_click_en_track_pagina(root, clean_hosts):
    host = _host(root, height=200, content_h=1000)
    host._show_now()
    root.update_idletasks()
    _x0, _y0, _x1, y1 = host.bar.bbox("sthumb")
    h = host.bar.winfo_height()
    assert y1 < h - 2
    host.bar.event_generate("<Button-1>", x=6, y=h - 2)
    root.update()
    assert host.canvas.yview()[0] > 0.0
