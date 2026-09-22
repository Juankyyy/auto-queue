"""
main.py — Interfaz gráfica premium para el bot de auto-aceptación de LoL
"""

import calendar
import ctypes
import math
import os
import socket
import sys
import threading
import time
import tkinter as tk
from datetime import datetime, timedelta

from PIL import Image, ImageTk

import icons
from bot import LoLAutoAccept
from config_store import load_config, save_config
from i18n import get_language, set_language, t
from paths import bundled_path, migrate_user_file, user_data_dir
from stats_store import MAX_STATS_EVENTS, StatsStore
from tray import SystemTray

# Identificador de aplicación para que Windows muestre el icono propio en la barra de tareas
# + conciencia DPI para que captura (ImageGrab) y clics usen las mismas coordenadas.
try:
    myappid = "lol.autoaccept.bot.app.1.0"
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)  # Per-monitor V2
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass
except Exception:
    pass


_MAX_LOG_LINES = 500


def _load_version():
    """Lee la versión desde version.txt (empaquetado en el .exe)."""
    try:
        with open(bundled_path("version.txt"), encoding="utf-8") as f:
            return f.read().strip() or "0.0.0-dev"
    except Exception:
        return "0.0.0-dev"


# ──────────────────────────────────────────────
# Paleta de colores
# ──────────────────────────────────────────────
BG        = "#0D1117"
CARD      = "#161B22"
BORDER    = "#21262D"
GOLD      = "#C89B3C"
GOLD_DIM  = "#8A6A27"
CYAN      = "#00E5FF"
CYAN_DIM  = "#007A8A"
GREEN     = "#00E676"
RED       = "#FF4757"
TEXT      = "#C9D1D9"
TEXT_DIM  = "#6E7681"
WHITE     = "#F0F6FC"


class AnimatedDot(tk.Canvas):
    """Indicador de estado con halo expansivo suave (doble ripple + respiración)."""

    def __init__(self, parent, size=22, **kwargs):
        super().__init__(parent, width=size, height=size,
                         bg=CARD, highlightthickness=0, **kwargs)
        self.size = size
        self.active = False
        self._phase = 0.0
        self._job = None
        self._draw_idle()

    @staticmethod
    def _blend(fg, bg, t):
        """Mezcla dos colores hex; t=0 -> fg, t=1 -> bg (simula alfa sobre CARD)."""
        fg = fg.lstrip("#")
        bg = bg.lstrip("#")
        r = int(int(fg[0:2], 16) * (1 - t) + int(bg[0:2], 16) * t)
        g = int(int(fg[2:4], 16) * (1 - t) + int(bg[2:4], 16) * t)
        b = int(int(fg[4:6], 16) * (1 - t) + int(bg[4:6], 16) * t)
        return f"#{r:02X}{g:02X}{b:02X}"

    def _draw_idle(self):
        self.delete("all")
        c = self.size / 2
        r = 4
        self.create_oval(c - r, c - r, c + r, c + r, fill=RED, outline="")

    def set_active(self, active: bool):
        self.active = active
        if active:
            if self._job is None:
                self._animate()
        else:
            if self._job is not None:
                try:
                    self.after_cancel(self._job)
                except Exception:
                    pass
                self._job = None
            self._draw_idle()

    def _animate(self):
        if not self.active:
            self._job = None
            return
        self._phase = (self._phase + 0.04) % 1.0
        self.delete("all")
        c = self.size / 2
        max_r = c - 1

        # Ondas expansivas (dos, desfasadas, con easing de salida)
        for offset in (0.0, 0.5):
            p = (self._phase + offset) % 1.0
            eased = 1.0 - (1.0 - p) ** 2
            rr = 5.0 + eased * (max_r - 5.0)
            color = self._blend(GREEN, CARD, min(1.0, 0.15 + 0.85 * p))
            self.create_oval(c - rr, c - rr, c + rr, c + rr,
                             outline=color, width=2)

        # Resplandor suave bajo el núcleo
        glow_r = 6.5
        self.create_oval(c - glow_r, c - glow_r, c + glow_r, c + glow_r,
                         fill=self._blend(GREEN, CARD, 0.78), outline="")

        # Núcleo con respiración gentil
        core_r = 4.1 * (0.94 + 0.06 * math.sin(self._phase * 2 * math.pi))
        self.create_oval(c - core_r, c - core_r, c + core_r, c + core_r,
                         fill=GREEN, outline="")

        self._job = self.after(30, self._animate)


class GlowButton(tk.Canvas):
    """Botón grande con efecto glow personalizable."""

    def __init__(self, parent, text_on="START BOT", text_off="STOP BOT",
                 command=None, **kwargs):
        super().__init__(parent, width=230, height=58,
                         bg=BG, highlightthickness=0, cursor="hand2",
                          takefocus=True, highlightcolor=CYAN, **kwargs)
        self.text_on = text_on
        self.text_off = text_off
        self.command = command
        self.is_on = False
        self._draw()
        self.bind("<Button-1>", self._on_click)
        self.bind("<Return>", self._on_key)
        self.bind("<KP_Enter>", self._on_key)
        self.bind("<space>", self._on_key)
        self.bind("<FocusIn>", self._on_focus_in)
        self.bind("<FocusOut>", self._on_focus_out)
        self.bind("<Enter>", self._on_hover)
        self.bind("<Leave>", self._on_leave)
        self._hovered = False
        self._focused = False

    def _draw(self, hover=False):
        self.delete("all")
        w, h = 230, 58
        r = 10  # radio de esquinas

        if self.is_on:
            fill_color   = "#0D2F2F" if not hover else "#0F3A3A"
            border_color = CYAN
            text_color   = CYAN
            label        = self.text_off
        else:
            fill_color   = "#1E1A0E" if not hover else "#26210F"
            border_color = GOLD
            text_color   = GOLD
            label        = self.text_on

        # Sombra/glow
        glow_color = CYAN_DIM if self.is_on else GOLD_DIM
        for i in range(4, 0, -1):
            alpha_color = glow_color
            self.create_rounded_rect(i, i, w - i, h - i, radius=r + i,
                                     outline=alpha_color, fill="")

        # Fondo del botón
        self.create_rounded_rect(3, 3, w - 3, h - 3, radius=r,
                                 fill=fill_color, outline=border_color, width=2)

        # Texto
        self.create_text(w // 2, h // 2, text=label,
                         font=("Cascadia Code", 13, "bold"), fill=text_color)

    def create_rounded_rect(self, x1, y1, x2, y2, radius=10, **kwargs):
        points = [
            x1 + radius, y1,
            x2 - radius, y1,
            x2, y1,
            x2, y1 + radius,
            x2, y2 - radius,
            x2, y2,
            x2 - radius, y2,
            x1 + radius, y2,
            x1, y2,
            x1, y2 - radius,
            x1, y1 + radius,
            x1, y1,
        ]
        return self.create_polygon(points, smooth=True, **kwargs)

    def set_state(self, is_on: bool):
        self.is_on = is_on
        self._draw(self._hovered or self._focused)

    def _on_click(self, _):
        try:
            self.focus_set()
        except Exception:
            pass
        if self.command:
            self.command()

    def _on_key(self, event):
        if event.keysym in ("Return", "KP_Enter", "space"):
            self._on_click(event)
            return "break"

    def _on_focus_in(self, _):
        self._focused = True
        self._draw(hover=True)

    def _on_focus_out(self, _):
        self._focused = False
        self._draw(hover=self._hovered)

    def _on_hover(self, _):
        self._hovered = True
        self._draw(hover=True)

    def _on_leave(self, _):
        self._hovered = False
        self._draw(hover=self._focused)


class CloseButton(tk.Canvas):
    """Boton cerrar con X dibujada (simetrica y nitida a cualquier escala)."""

    def __init__(self, parent, command=None, size=38, **kwargs):
        super().__init__(parent, width=size, height=36,
                         bg=BG, highlightthickness=0, cursor="hand2", **kwargs)
        self.command = command
        self._size = size
        self._draw(False)
        self.bind("<Button-1>", self._on_click)
        self.bind("<Enter>", lambda _: self._draw(True))
        self.bind("<Leave>", lambda _: self._draw(False))

    def _draw(self, hover):
        self.delete("all")
        w = self._size
        self.create_rectangle(0, 0, w, 36, fill=RED if hover else BG,
                              outline="")
        color = WHITE if hover else TEXT_DIM
        self.create_text(w / 2, 19, text=icons.glyph("xmark"),
                         font=(icons.family(), 12), fill=color)

    def _on_click(self, _):
        if self.command:
            self.command()


class TitleIcon(tk.Canvas):
    """Icono de la fuente Font Awesome (tintable, nitido a todo DPI)."""

    def __init__(self, parent, glyph, command=None, size=38, height=36,
                 bg=BG, fg=TEXT_DIM, hover_fg=WHITE, active_fg=None,
                 font_size=13, **kwargs):
        super().__init__(parent, width=size, height=height,
                         bg=bg, highlightthickness=0, cursor="hand2",
                         takefocus=True, highlightcolor=hover_fg, **kwargs)
        self._glyph = glyph
        self._font = (icons.family(), font_size)
        self.command = command
        self._size = size
        self._height = height
        self._bg = bg
        self._fg = fg
        self._hover_fg = hover_fg
        self._active_fg = active_fg if active_fg is not None else hover_fg
        self._hovered = False
        self._active = False
        self._draw()
        self.bind("<Button-1>", self._on_click)
        self.bind("<Return>", self._on_key)
        self.bind("<KP_Enter>", self._on_key)
        self.bind("<space>", self._on_key)
        self.bind("<Enter>", self._on_hover)
        self.bind("<Leave>", self._on_leave)

    def _draw(self):
        self.delete("all")
        color = self._active_fg if self._active else (
            self._hover_fg if self._hovered else self._fg)
        self.create_rectangle(0, 0, self._size, self._height,
                              fill=self._bg if not self._hovered else BORDER,
                              outline="")
        self.create_text(self._size / 2, self._height / 2 + 1,
                         text=self._glyph, font=self._font, fill=color)

    def set_active(self, active):
        self._active = bool(active)
        self._draw()

    def _on_click(self, _):
        try:
            self.focus_set()
        except Exception:
            pass
        if self.command:
            self.command()

    def _on_key(self, event):
        if event.keysym in ("Return", "KP_Enter", "space"):
            self._on_click(event)
            return "break"

    def _on_hover(self, _):
        self._hovered = True
        self._draw()

    def _on_leave(self, _):
        self._hovered = False
        self._draw()


class HexIcon(tk.Canvas):
    """Icono hexagonal estilo LoL."""

    def __init__(self, parent, size=44, **kwargs):
        super().__init__(parent, width=size, height=size,
                         bg=BG, highlightthickness=0, **kwargs)
        self._draw(size)

    def _draw(self, size):
        cx, cy = size / 2, size / 2
        r_outer = size / 2 - 2
        r_inner = r_outer * 0.65
        pts_outer = self._hex_points(cx, cy, r_outer)
        pts_inner = self._hex_points(cx, cy, r_inner)

        # Relleno oscuro
        self.create_polygon(pts_outer, fill="#0D1117", outline=GOLD, width=2)
        # Hexágono interior cyan
        self.create_polygon(pts_inner, fill="", outline=CYAN, width=1)
        # Letra central
        self.create_text(cx, cy, text="L", font=("Cascadia Code", int(size * 0.3), "bold"),
                         fill=GOLD)

    @staticmethod
    def _hex_points(cx, cy, r):
        pts = []
        for i in range(6):
            angle = math.radians(60 * i - 30)
            pts.extend([cx + r * math.cos(angle), cy + r * math.sin(angle)])
        return pts


class Divider(tk.Frame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg=BORDER, height=1, **kwargs)


class ScrollHost(tk.Frame):
    """Página con scroll vertical: rueda del mouse + pastilla moderna flotante.

    Una sola rueda global (bind_all una vez) se enruta al ScrollHost que
    está bajo el cursor. La barra es un canvas flotante (no ocupa espacio)
    con un thumb redondeado, visible solo si el contenido desborda; los
    items del thumb son persistentes (se mueven y tiñen, nunca se borran
    en caliente) y mostrarla se difiere para no parpadear en transiciones.
    """

    _instances = []
    _wheel_bound = False

    BAR_W = 12
    THUMB_W = 6
    THUMB_MIN = 28

    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg=BG, **kwargs)
        self.canvas = tk.Canvas(self, bg=BG, highlightthickness=0, bd=0)
        self.inner = tk.Frame(self.canvas, bg=BG)
        self._win = self.canvas.create_window((0, 0), window=self.inner,
                                              anchor="nw")
        self.bar = tk.Canvas(self, width=self.BAR_W, bg=BG,
                             highlightthickness=0, bd=0)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.canvas.configure(yscrollcommand=self._on_scroll)
        self.inner.bind("<Configure>", lambda _: self._after_layout())
        self.canvas.bind("<Configure>", self._on_canvas_resize)
        self.bar.bind("<Button-1>", self._track_click)
        x0 = (self.BAR_W - self.THUMB_W) / 2
        x1 = x0 + self.THUMB_W
        self._thumb_items = (
            self.bar.create_rectangle(x0, -10, x1, -10, fill="#2D333B",
                                      outline="", tags="sthumb"),
            self.bar.create_oval(x0, -10, x1, -10, fill="#2D333B",
                                 outline="", tags="sthumb"),
            self.bar.create_oval(x0, -10, x1, -10, fill="#2D333B",
                                 outline="", tags="sthumb"),
        )
        self.bar.tag_bind("sthumb", "<Enter>", lambda _: self._set_hover(True))
        self.bar.tag_bind("sthumb", "<Leave>", lambda _: self._set_hover(False))
        self.bar.tag_bind("sthumb", "<Button-1>", self._drag_start)
        self.bar.tag_bind("sthumb", "<B1-Motion>", self._drag_move)
        self.bar.tag_bind("sthumb", "<ButtonRelease-1>", self._drag_end)
        self.bar.bind("<ButtonRelease-1>", self._drag_end)
        self._frac = (0.0, 1.0)
        self._hover = False
        self._drag_root = None
        self._drag_first = 0.0
        self._bar_placed = False
        self._show_job = None
        self._squelch_until = 0.0
        ScrollHost._instances.append(self)
        self.bind("<Destroy>", self._on_destroy)
        ScrollHost._ensure_wheel(self.canvas)

    # ── Layout ──

    def _after_layout(self):
        try:
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        except Exception:
            pass

    def _on_canvas_resize(self, event):
        try:
            self.canvas.itemconfig(self._win, width=event.width)
        except Exception:
            pass

    def _on_destroy(self, event):
        if event.widget is not self:
            return
        self._cancel_show()
        try:
            if self in ScrollHost._instances:
                ScrollHost._instances.remove(self)
        except Exception:
            pass

    # ── Visibilidad (mostrar diferido, ocultar inmediato) ──

    def _on_scroll(self, first, last):
        try:
            first, last = float(first), float(last)
        except Exception:
            return
        self._frac = (first, last)
        if first <= 0.0 and last >= 1.0:
            self._cancel_show()
            self._set_bar_visible(False)
        else:
            if self._bar_placed:
                self._position_thumb()
            else:
                self._schedule_show()

    SHOW_DELAY_MS = 350

    def squelch(self, ms=600):
        """Silencia la aparición de la barra por `ms` (transiciones de página)."""
        try:
            self._squelch_until = time.monotonic() + ms / 1000.0
        except Exception:
            pass

    def _schedule_show(self):
        if self._bar_placed or self._show_job is not None:
            return
        try:
            delay = int(self.SHOW_DELAY_MS)
            try:
                remaining = (self._squelch_until - time.monotonic()) * 1000.0
                if remaining > 0:
                    delay = int(max(delay, remaining))
            except Exception:
                pass
            self._show_job = self.after(delay, self._show_now)
        except Exception:
            pass

    def _show_now(self):
        self._show_job = None
        try:
            first, last = self.canvas.yview()
        except Exception:
            return
        if first <= 0.0 and last >= 1.0:
            return
        self._set_bar_visible(True)
        self._position_thumb()

    # ── Thumb (items persistentes: se mueven y tiñen, nunca se borran) ──

    def _thumb_color(self):
        if self._hover or self._drag_root is not None:
            return GOLD
        return "#2D333B"

    def _position_thumb(self):
        try:
            h = self.canvas.winfo_height()
            if h <= 1:
                return
            first, last = self._frac
            th = max(float(self.THUMB_MIN), (last - first) * h)
            y0 = max(0.0, min(first * h, h - th))
            y1 = min(float(h), y0 + th)
            x0 = (self.BAR_W - self.THUMB_W) / 2
            x1 = x0 + self.THUMB_W
            r = self.THUMB_W / 2
            color = self._thumb_color()
            self.bar.coords(self._thumb_items[0], x0, y0 + r, x1, y1 - r)
            self.bar.coords(self._thumb_items[1], x0, y0, x1, y0 + 2 * r)
            self.bar.coords(self._thumb_items[2], x0, y1 - 2 * r, x1, y1)
            for _item in self._thumb_items:
                self.bar.itemconfig(_item, fill=color)
        except Exception:
            pass

    def _set_hover(self, on):
        self._hover = on
        self._position_thumb()

    def _drag_start(self, event):
        self._drag_root = event.y_root
        self._drag_first = self._frac[0]
        self._position_thumb()
        return "break"

    def _drag_move(self, event):
        if self._drag_root is None:
            return "break"
        try:
            h = self.canvas.winfo_height()
            if h <= 1:
                return "break"
            target = self._drag_first + (event.y_root - self._drag_root) / h
            self.canvas.yview_moveto(max(0.0, min(1.0, target)))
        except Exception:
            pass
        return "break"

    def _drag_end(self, event):
        self._drag_root = None
        self._position_thumb()
        return "break"

    def _track_click(self, event):
        try:
            y0 = self._frac[0] * self.canvas.winfo_height()
            self.canvas.yview_scroll(-1 if event.y < y0 else 1, "pages")
        except Exception:
            pass

    def _cancel_show(self):
        if self._show_job is not None:
            try:
                self.after_cancel(self._show_job)
            except Exception:
                pass
            self._show_job = None

    def _set_bar_visible(self, vis):
        if vis == self._bar_placed:
            return
        self._bar_placed = vis
        try:
            if vis:
                self.bar.place(relx=1.0, rely=0.0, width=self.BAR_W,
                               relheight=1.0, anchor="ne")
            else:
                self.bar.place_forget()
        except Exception:
            pass

    # ── Rueda global ──

    @classmethod
    def _ensure_wheel(cls, widget):
        if cls._wheel_bound:
            return
        cls._wheel_bound = True
        try:
            widget.bind_all("<MouseWheel>", cls._route_wheel)
        except Exception:
            cls._wheel_bound = False

    @classmethod
    def _route_wheel(cls, event):
        try:
            w = event.widget.winfo_containing(event.x_root, event.y_root)
        except Exception:
            return
        if w is None:
            return
        for inst in list(cls._instances):
            try:
                if not inst.winfo_ismapped():
                    continue
                if str(w).startswith(str(inst.canvas)):
                    steps = -1 * (event.delta // 120)
                    if steps == 0:
                        steps = -1 if event.delta > 0 else 1
                    inst.canvas.yview_scroll(steps, "units")
                    return "break"
            except Exception:
                continue


class App:
    def __init__(self):
        self.root = tk.Tk()
        self.version = _load_version()
        self.root.title("LoL Auto Queue")
        self.root.geometry("390x560")
        self.root.resizable(False, False)
        self.root.configure(bg=BG)
        # Ventana sin decoración nativa de Windows (frameless)
        self.root.overrideredirect(True)
        self._drag_x = 0
        self._drag_y = 0
        self.base_dir = user_data_dir()
        # Migra config/stats/template desde la carpeta de la app (ubicación anterior).
        migrate_user_file("config.json")
        migrate_user_file("stats.json")
        migrate_user_file(os.path.join("templates", "accept_btn.png"),
                          os.path.join("assets", "templates", "accept_btn.png"))
        self._config_path = os.path.join(self.base_dir, "config.json")

        self._center_window(390, 560)
        self._apply_frameless_style()

        # Configurar icono de ventana y barra de tareas (nuevo icono primero)
        ico_path = bundled_path("assets", "icons", "app_icon.ico")
        logo_path = None
        for candidate in (bundled_path("assets", "icons", "app_icon.png"),
                          bundled_path("assets", "templates", "logo.png")):
            if os.path.exists(candidate):
                logo_path = candidate
                break

        if os.path.exists(ico_path):
            try:
                self.root.iconbitmap(default=ico_path)
            except Exception:
                pass

        if logo_path is not None:
            try:
                self._icon_img = ImageTk.PhotoImage(file=logo_path)
                self.root.iconphoto(True, self._icon_img)
            except Exception:
                pass

        # Estado y variables de configuración (persistentes en config.json)
        saved = self._load_config()
        set_language(saved.get("lang", "en"))
        self.bot_active = False
        self.bot_thread = None
        self._save_cfg_job = None
        self._log_visible = bool(saved.get("log_visible", True))
        self._win_h_full = 560
        self.delay_val = tk.DoubleVar(value=saved["delay"])
        self.thresh_val = tk.DoubleVar(value=saved["threshold"])
        self.auto_deactivate_var = tk.BooleanVar(value=saved["auto_deactivate"])
        self.close_to_tray_var = tk.BooleanVar(value=saved["close_to_tray"])
        self._tray = None
        self._window_visible = True
        # Estadísticas de uso (persistentes en stats.json)
        self._stats_path = os.path.join(self.base_dir, "stats.json")
        self._stats_store = StatsStore(self._stats_path)
        self._stats_store.load()
        self._stats = self._stats_store.data
        self._session_start = None
        # Navegación PWA por páginas dentro de la misma ventana
        self._page = "home"
        self._pages = {}
        self._settings_built = False
        self._stats_built = False
        self._stats_tick_on = False
        self._page_heights = {"home": 560, "settings": 720, "stats": 660}
        self._stats_period = "day"
        self._stats_ref = datetime.now()
        self._win_pos = saved.get("pos")

        self.bot = LoLAutoAccept(
            log_callback=self._log,
            accepted_callback=self._on_partida_aceptada
        )

        self._build_ui()
        self._setup_tray()
        self._set_log_visible(self._log_visible, save=False)
        self._restore_pos(saved.get("pos"))
        self._pos_job = None
        self.root.bind("<Configure>", lambda _: self._schedule_pos_save())

    # ──────────────────────────────────────────
    # Construcción de la UI Principal
    # ──────────────────────────────────────────

    def _build_ui(self):
        root = self.root

        # ── Barra de título personalizada (arrastrable) ──
        titlebar = tk.Frame(root, bg=BG, height=36)
        titlebar.pack(fill="x", side="top")
        titlebar.pack_propagate(False)

        titlebar.bind("<ButtonPress-1>", self._start_move)
        titlebar.bind("<B1-Motion>", self._on_move)

        tb_title = tk.Label(titlebar, text="LoL Auto Queue",
                            font=("Cascadia Code", 9), fg=TEXT_DIM, bg=BG)
        tb_title.pack(side="left", padx=12)
        self.tb_title = tb_title
        tb_title.bind("<ButtonPress-1>", self._start_move)
        tb_title.bind("<B1-Motion>", self._on_move)

        # Botones arriba a la derecha: Ajustes y Cerrar
        tb_close = CloseButton(titlebar, command=self._close_app)
        tb_close.pack(side="right")

        self.tb_cfg = TitleIcon(titlebar, icons.glyph("gear"),
                                command=lambda: self.show_page("settings"),
                                hover_fg=GOLD, active_fg=GOLD)
        self.tb_cfg.pack(side="right")
        self.tb_stats = TitleIcon(titlebar, icons.glyph("chart"),
                                  command=lambda: self.show_page("stats"),
                                  hover_fg=CYAN, active_fg=CYAN)
        self.tb_stats.pack(side="right")
        self.tb_home = TitleIcon(titlebar, icons.glyph("house"),
                                 command=lambda: self.show_page("home"),
                                 hover_fg=WHITE, active_fg=WHITE)
        self.tb_home.pack(side="right")

        # ── Header ──────────────────────────────
        header = tk.Frame(root, bg=BG)
        header.pack(fill="x", padx=24, pady=(10, 10))

        # Logo de la app (nuevo icono primero)
        logo_loaded = False
        for logo_path in (bundled_path("assets", "icons", "app_icon.png"),
                          bundled_path("assets", "templates", "logo.png")):
            if not os.path.exists(logo_path):
                continue
            try:
                pil_logo = Image.open(logo_path).resize((46, 46), Image.Resampling.LANCZOS)
                self.header_logo = ImageTk.PhotoImage(pil_logo)
                logo_lbl = tk.Label(header, image=self.header_logo, bg=BG)
                logo_lbl.pack(side="left")
                logo_loaded = True
                break
            except Exception:
                continue

        if not logo_loaded:
            HexIcon(header, size=46).pack(side="left")

        titles = tk.Frame(header, bg=BG)
        titles.pack(side="left", padx=12)
        tk.Label(titles, text="LoL Auto Queue",
                 font=("Cascadia Code", 16, "bold"), fg=GOLD, bg=BG).pack(anchor="w")

        Divider(root).pack(fill="x", padx=24, pady=(0, 0))

        # ── Tarjeta de estado ────────────────────
        status_card = tk.Frame(root, bg=CARD, pady=0)
        status_card.pack(fill="x", padx=24, pady=16)

        left = tk.Frame(status_card, bg=CARD)
        left.pack(side="left", padx=16, pady=14)

        self.dot = AnimatedDot(left, size=22)
        self.dot.pack(side="left")

        self.status_lbl = tk.Label(left, text=t("status_idle"),
                                   font=("Cascadia Code", 11, "bold"),
                                   fg=RED, bg=CARD)
        self.status_lbl.pack(side="left", padx=(8, 0))

        self.log_toggle_btn = TitleIcon(status_card, icons.glyph("note"),
                                        command=self._toggle_log, bg=CARD,
                                        hover_fg=GREEN, active_fg=GREEN)
        self.log_toggle_btn.pack(side="right", padx=16)
        self.log_toggle_btn.set_active(self._log_visible)

        # ── Botón toggle ─────────────────────────
        btn_frame = tk.Frame(root, bg=BG)
        btn_frame.pack(pady=(16, 20))

        self.toggle_btn = GlowButton(btn_frame, text_on=t("start_bot"),
                                     text_off=t("stop_bot"),
                                     command=self._toggle)
        self.toggle_btn.pack()

        # ── Pie con versión ────────────────────────
        footer = tk.Frame(root, bg=BG)
        footer.pack(side="bottom", fill="x", padx=24, pady=(10))
        tk.Label(footer, text=f"v{self.version}",
                 font=("Cascadia Code", 9), fg=TEXT_DIM, bg=BG).pack(side="right")
        Divider(root).pack(side="bottom", fill="x")

        # ── Log ──────────────────────────────────
        self.log_card = tk.Frame(root, bg=CARD)
        log_card = self.log_card
        log_card.pack(fill="both", expand=True, padx=24, pady=(0, 20))

        tk.Label(log_card, text=t("log_title"),
                 font=("Cascadia Code", 9, "bold"), fg=TEXT_DIM, bg=CARD
                 ).pack(anchor="w", padx=14, pady=(10, 4))

        self.log_box = tk.Text(
            log_card, height=8, bg="#090D12", fg="#3FB950",
            font=("Cascadia Mono", 8), relief="flat", state="disabled",
            wrap="word", padx=10, pady=8, insertbackground=CYAN,
            selectbackground=BORDER
        )
        self.log_box.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        self.log_box.tag_config("warn", foreground="#FFA657")
        self.log_box.tag_config("error", foreground=RED)
        self.log_box.tag_config("success", foreground=GREEN)
        self.log_box.tag_config("info", foreground="#3FB950")

        # ── Overlay de páginas internas (ajustes / estadísticas) ──
        self.page_overlay = tk.Frame(root, bg=BG)
        self._pages = {}
        for _name in ("settings", "stats"):
            _scroll = ScrollHost(self.page_overlay)
            _scroll.pack(fill="both", expand=True)
            _scroll.pack_forget()
            self._pages[_name] = _scroll

        self._update_nav_highlight()
        self._log(t("boot_msg"))

    # ──────────────────────────────────────────
    # Navegación por páginas (ventana única)
    # ──────────────────────────────────────────

    def _nav_leave(self, widget, page, color):
        # (compat: el resaltado real lo gestiona TitleIcon.set_active)
        self._update_nav_highlight()

    def _update_nav_highlight(self):
        try:
            self.tb_cfg.set_active(self._page == "settings")
        except Exception:
            pass
        try:
            self.tb_stats.set_active(self._page == "stats")
        except Exception:
            pass
        try:
            self.tb_home.set_active(self._page == "home")
        except Exception:
            pass

    def show_page(self, name):
        """Cambia de página dentro de la misma ventana (estilo PWA)."""
        if name not in ("home", "settings", "stats"):
            return
        try:
            if name == "settings" and not self._settings_built:
                self._build_settings_page()
            if name == "stats" and not self._stats_built:
                self._build_stats_page()
            self._page = name
            for _pg in self._pages.values():
                _pg.pack_forget()
            if name != "stats":
                self._stats_tick_on = False
            if name == "home":
                self.page_overlay.place_forget()
                self.tb_title.config(text="LoL Auto Queue")
                self.root.update_idletasks()
                if self._log_visible:
                    self.root.geometry(f"390x{self._win_h_full or 560}")
                else:
                    self.root.geometry(f"390x{self.root.winfo_reqheight()}")
            else:
                self._pages[name].pack(fill="both", expand=True)
                self.page_overlay.place(x=0, y=36, relwidth=1.0,
                                        relheight=1.0, height=-36)
                self.page_overlay.lift()
                try:
                    self._pages[name]._set_bar_visible(False)
                    self._pages[name].squelch(600)
                except Exception:
                    pass
                self.tb_title.config(
                    text=t("page_settings") if name == "settings" else t("page_stats"))
                self.root.geometry(f"390x{self._page_heights[name]}")
                self.root.update_idletasks()
            self._update_nav_highlight()
            if name == "stats":
                self._select_period(self._stats_period)
                if not self._stats_tick_on:
                    self._stats_tick_on = True
                    self._stats_tick()
        except Exception:
            pass

    def _open_settings_page(self):
        self._show_window()
        self.show_page("settings")

    # ──────────────────────────────────────────
    # Menú de Configuración Separado
    # ──────────────────────────────────────────

    def _build_settings_page(self):
        """Construye la página de ajustes dentro de la ventana (una sola vez)."""
        if self._settings_built:
            return
        self._settings_built = True
        body = self._pages["settings"].inner

        # Encabezado de Ajustes
        s_header = tk.Frame(body, bg=BG)
        s_header.pack(fill="x", padx=20, pady=(14, 4))

        tk.Label(s_header, text=t("settings_title"), font=("Cascadia Code", 13, "bold"),
                 fg=GOLD, bg=BG).pack(side="left")

        Divider(body).pack(fill="x", padx=20, pady=(0, 14))

        # Tarjeta 1: Ajustes de detección (sliders)
        cfg_card = tk.Frame(body, bg=CARD)
        cfg_card.pack(fill="x", padx=20, pady=0)

        tk.Label(cfg_card, text=t("det_times"),
                 font=("Cascadia Code", 9, "bold"), fg=TEXT_DIM, bg=CARD
                 ).pack(anchor="w", padx=16, pady=(12, 8))

        # Slider Delay
        self._make_slider(cfg_card, t("delay_label"), "delay_val", "delay_lbl",
                          from_=0.1, to=3.0, resolution=0.1, default=0.5,
                          fmt=lambda v: f"{v:.1f}s")

        # Slider Umbral
        self._make_slider(cfg_card, t("threshold_label"), "thresh_val", "thresh_lbl",
                          from_=0.50, to=0.99, resolution=0.01, default=0.80,
                          fmt=lambda v: f"{int(v*100)}%")

        # Tarjeta 2: Comportamiento tras aceptar
        beh_card = tk.Frame(body, bg=CARD)
        beh_card.pack(fill="x", padx=20, pady=(10, 0))

        tk.Label(beh_card, text=t("on_accept"),
                 font=("Cascadia Code", 9, "bold"), fg=TEXT_DIM, bg=CARD
                 ).pack(anchor="w", padx=16, pady=(12, 8))

        beh_btns_frame = tk.Frame(beh_card, bg=CARD)
        beh_btns_frame.pack(fill="x", padx=16, pady=(0, 8))

        btn_deact = tk.Label(beh_btns_frame, text=t("disable_bot"),
                             font=("Cascadia Code", 10, "bold"), cursor="hand2",
                             pady=7, padx=8)
        btn_deact.pack(side="left", fill="x", expand=True, padx=(0, 4))

        btn_keep = tk.Label(beh_btns_frame, text=t("keep_active"),
                            font=("Cascadia Code", 10, "bold"), cursor="hand2",
                            pady=7, padx=8)
        btn_keep.pack(side="right", fill="x", expand=True, padx=(4, 0))

        beh_desc = tk.Label(beh_card, text="", font=("Cascadia Code", 9),
                            fg=TEXT_DIM, bg=CARD, wraplength=300, justify="left")
        beh_desc.pack(anchor="w", padx=16, pady=(0, 12))

        def update_beh_ui():
            if self.auto_deactivate_var.get():
                btn_deact.config(bg="#152636", fg=CYAN)
                btn_keep.config(bg=BORDER, fg=TEXT_DIM)
                beh_desc.config(text=t("beh_disable_desc"))
            else:
                btn_deact.config(bg=BORDER, fg=TEXT_DIM)
                btn_keep.config(bg="#2E2410", fg=GOLD)
                beh_desc.config(text=t("beh_keep_desc"))

        def select_deact(_=None):
            self.auto_deactivate_var.set(True)
            self.bot.auto_deactivate = True
            update_beh_ui()
            self._save_config()

        def select_keep(_=None):
            self.auto_deactivate_var.set(False)
            self.bot.auto_deactivate = False
            update_beh_ui()
            self._save_config()

        btn_deact.bind("<Button-1>", select_deact)
        btn_keep.bind("<Button-1>", select_keep)
        update_beh_ui()

        # Tarjeta 3: Calibración / template
        tpl_card = tk.Frame(body, bg=CARD)
        tpl_card.pack(fill="x", padx=20, pady=10)

        tk.Label(tpl_card, text=t("tpl_title"),
                 font=("Cascadia Code", 9, "bold"), fg=TEXT_DIM, bg=CARD
                 ).pack(anchor="w", padx=16, pady=(12, 4))

        tk.Label(tpl_card, text=t("tpl_desc"),
                 font=("Cascadia Code", 9), fg=TEXT_DIM, bg=CARD, wraplength=300, justify="left"
                 ).pack(anchor="w", padx=16, pady=(0, 8))

        cal_btn = tk.Label(tpl_card,
                           text=t("capture_btn"),
                           font=("Cascadia Code", 10, "bold"), fg=CYAN, bg=BORDER,
                           cursor="hand2", pady=7, padx=10)
        cal_btn.pack(padx=16, pady=(0, 14), anchor="w")
        cal_btn.bind("<Button-1>", lambda e: self._calibrate())
        cal_btn.bind("<Enter>", lambda _: cal_btn.config(bg="#2D333B", fg=WHITE))
        cal_btn.bind("<Leave>", lambda _: cal_btn.config(bg=BORDER, fg=CYAN))

        # Tarjeta 4: Comportamiento al cerrar la app
        close_card = tk.Frame(body, bg=CARD)
        close_card.pack(fill="x", padx=20, pady=(0, 10))

        tk.Label(close_card, text=t("on_close"),
                 font=("Cascadia Code", 9, "bold"), fg=TEXT_DIM, bg=CARD
                 ).pack(anchor="w", padx=16, pady=(12, 8))

        close_btns_frame = tk.Frame(close_card, bg=CARD)
        close_btns_frame.pack(fill="x", padx=16, pady=(0, 8))

        btn_quit = tk.Label(close_btns_frame, text=t("quit_btn"),
                            font=("Cascadia Code", 10, "bold"), cursor="hand2",
                            pady=7, padx=8)
        btn_quit.pack(side="left", fill="x", expand=True, padx=(0, 4))

        btn_tray = tk.Label(close_btns_frame, text=t("tray_btn"),
                            font=("Cascadia Code", 10, "bold"), cursor="hand2",
                            pady=7, padx=8)
        btn_tray.pack(side="right", fill="x", expand=True, padx=(4, 0))

        close_desc = tk.Label(close_card, text="", font=("Cascadia Code", 9),
                              fg=TEXT_DIM, bg=CARD, wraplength=300, justify="left")
        close_desc.pack(anchor="w", padx=16, pady=(0, 12))

        def update_close_ui():
            if self.close_to_tray_var.get():
                btn_tray.config(bg="#152636", fg=CYAN)
                btn_quit.config(bg=BORDER, fg=TEXT_DIM)
                close_desc.config(text=t("close_tray_desc"))
            else:
                btn_tray.config(bg=BORDER, fg=TEXT_DIM)
                btn_quit.config(bg="#2E2410", fg=GOLD)
                close_desc.config(text=t("close_quit_desc"))

        def select_quit(_=None):
            self.close_to_tray_var.set(False)
            update_close_ui()
            self._save_config()

        def select_tray(_=None):
            self.close_to_tray_var.set(True)
            update_close_ui()
            self._save_config()

        btn_quit.bind("<Button-1>", select_quit)
        btn_tray.bind("<Button-1>", select_tray)
        update_close_ui()

        # Tarjeta 5: Idioma
        lang_card = tk.Frame(body, bg=CARD)
        lang_card.pack(fill="x", padx=20, pady=(0, 10))

        tk.Label(lang_card, text=t("lang_title"),
                 font=("Cascadia Code", 9, "bold"), fg=TEXT_DIM, bg=CARD
                 ).pack(anchor="w", padx=16, pady=(12, 8))

        lang_btns_frame = tk.Frame(lang_card, bg=CARD)
        lang_btns_frame.pack(fill="x", padx=16, pady=(0, 8))

        btn_en = tk.Label(lang_btns_frame, text="English",
                          font=("Cascadia Code", 10, "bold"), cursor="hand2",
                          pady=7, padx=8)
        btn_en.pack(side="left", fill="x", expand=True, padx=(0, 4))

        btn_es = tk.Label(lang_btns_frame, text="Español",
                          font=("Cascadia Code", 10, "bold"), cursor="hand2",
                          pady=7, padx=8)
        btn_es.pack(side="right", fill="x", expand=True, padx=(4, 0))

        lang_desc = tk.Label(lang_card, text=t("lang_desc"),
                             font=("Cascadia Code", 9),
                             fg=TEXT_DIM, bg=CARD, wraplength=300, justify="left")
        lang_desc.pack(anchor="w", padx=16, pady=(0, 12))

        self._lang_btns = {"en": btn_en, "es": btn_es}

        def update_lang_ui():
            for _code, _btn in self._lang_btns.items():
                if _code == get_language():
                    _btn.config(bg="#152636", fg=CYAN)
                else:
                    _btn.config(bg=BORDER, fg=TEXT_DIM)

        def select_lang(code, _=None):
            if code == get_language():
                update_lang_ui()
                return
            set_language(code)
            self._save_config()
            update_lang_ui()
            self._restart_app()

        btn_en.bind("<Button-1>", lambda _: select_lang("en"))
        btn_es.bind("<Button-1>", lambda _: select_lang("es"))
        update_lang_ui()

    # ──────────────────────────────────────────
    # Página de Estadísticas (dentro de la ventana)
    # ──────────────────────────────────────────

    def _build_stats_page(self):
        """Construye la página de estadísticas dentro de la ventana (una sola vez)."""
        if self._stats_built:
            return
        self._stats_built = True
        body = self._pages["stats"].inner

        # Encabezado
        header = tk.Frame(body, bg=BG)
        header.pack(fill="x", padx=20, pady=(14, 4))
        tk.Label(header, text=t("stats_title"), font=("Cascadia Code", 12, "bold"),
                 fg=GOLD, bg=BG).pack(side="left")

        Divider(body).pack(fill="x", padx=20, pady=(6, 12))

        # ── Selector de periodo ──
        per_card = tk.Frame(body, bg=CARD)
        per_card.pack(fill="x", padx=20, pady=0)
        tk.Label(per_card, text=t("period_title"),
                 font=("Cascadia Code", 9, "bold"), fg=TEXT_DIM, bg=CARD
                 ).pack(anchor="w", padx=16, pady=(12, 8))

        per_row = tk.Frame(per_card, bg=CARD)
        per_row.pack(fill="x", padx=16, pady=(0, 12))

        self._period_btns = {}
        for key, tkey in (("day", "period_day"), ("week", "period_week"),
                          ("month", "period_month"), ("year", "period_year")):
            txt = t(tkey)
            btn = tk.Label(per_row, text=txt, font=("Cascadia Code", 9, "bold"),
                           cursor="hand2", pady=7)
            btn.pack(side="left", fill="x", expand=True,
                     padx=(0, 4) if key != "year" else (0, 0))
            btn.bind("<Button-1>", lambda _, k=key: self._select_period(k))
            self._period_btns[key] = btn

        # ── Navegación por periodo ──
        nav_row = tk.Frame(per_card, bg=CARD)
        nav_row.pack(fill="x", padx=16, pady=(0, 12))

        self._stats_prev = tk.Label(nav_row, text="<", font=("Cascadia Code", 10, "bold"),
                                    fg=TEXT_DIM, bg=CARD, cursor="hand2", width=3)
        self._stats_prev.pack(side="left")
        self._stats_prev.bind("<Button-1>", lambda _: self._stats_step(-1))
        self._stats_prev.bind("<Enter>", lambda _: self._stats_prev.config(fg=WHITE)
                              if not self._stats_at_first() else None)
        self._stats_prev.bind("<Leave>", lambda _: self._stats_prev.config(
            fg=BORDER if self._stats_at_first() else TEXT_DIM))

        self._stats_period_lbl = tk.Label(nav_row, text="", font=("Cascadia Code", 9, "bold"),
                                          fg=CYAN, bg=CARD)
        self._stats_period_lbl.pack(side="left", fill="x", expand=True)

        self._stats_next = tk.Label(nav_row, text=">", font=("Cascadia Code", 10, "bold"),
                                    fg=TEXT_DIM, bg=CARD, cursor="hand2", width=3)
        self._stats_next.pack(side="right")
        self._stats_next.bind("<Button-1>", lambda _: self._stats_step(1))
        self._stats_next.bind("<Enter>", lambda _: self._stats_next.config(fg=WHITE)
                              if not self._stats_at_present() else None)
        self._stats_next.bind("<Leave>", lambda _: self._stats_next.config(
            fg=BORDER if self._stats_at_present() else TEXT_DIM))

        # ── Tarjeta de valores ──
        stats_card = tk.Frame(body, bg=CARD)
        stats_card.pack(fill="x", padx=20, pady=(10, 0))

        self._stats_values = {}
        for key, tkey, color in (
            ("matches", "st_matches", CYAN),
            ("activations", "st_activations", WHITE),
            ("time", "st_time", GREEN),
            ("avg_act", "st_avg_act", WHITE),
            ("avg_sess", "st_avg_sess", WHITE),
            ("live", "st_live", GREEN),
        ):
            label = t(tkey)
            row = tk.Frame(stats_card, bg=CARD)
            row.pack(fill="x", padx=16, pady=5)
            tk.Label(row, text=label, font=("Cascadia Code", 9),
                     fg=TEXT_DIM, bg=CARD).pack(side="left")
            val = tk.Label(row, text="—", font=("Cascadia Code", 10, "bold"),
                           fg=color, bg=CARD)
            val.pack(side="right")
            self._stats_values[key] = val
        tk.Frame(stats_card, bg=CARD, height=8).pack()

        # ── Restablecer ──
        reset_btn = tk.Label(body, text=t("reset_stats"),
                             font=("Cascadia Code", 9, "bold"), fg=TEXT_DIM, bg=BORDER,
                             cursor="hand2", pady=8)
        reset_btn.pack(fill="x", padx=20, pady=(10, 0))
        reset_state = {"confirm": False}

        def _do_reset(_=None):
            if not reset_state["confirm"]:
                reset_state["confirm"] = True
                reset_btn.config(text=t("reset_confirm"), fg=RED)
                self.root.after(3000, lambda: (reset_state.update(confirm=False),
                                         reset_btn.config(
                                             text=t("reset_stats"),
                                             fg=TEXT_DIM))
                          if self._page == "stats" else None)
                return
            self._stats_store.reset()
            self._stats = self._stats_store.data
            reset_state["confirm"] = False
            reset_btn.config(text=t("reset_stats"), fg=TEXT_DIM)
            self._refresh_stats_win()
            self._log(t("stats_reset_done"))

        reset_btn.bind("<Button-1>", _do_reset)
        reset_btn.bind("<Enter>", lambda _: reset_btn.config(bg="#2D333B", fg=WHITE)
                       if not reset_state["confirm"] else None)
        reset_btn.bind("<Leave>", lambda _: reset_btn.config(bg=BORDER, fg=TEXT_DIM)
                       if not reset_state["confirm"] else None)


    def _select_period(self, period):
        self._stats_period = period
        self._stats_ref = datetime.now()
        for key, btn in getattr(self, "_period_btns", {}).items():
            if key == period:
                btn.config(bg="#152636", fg=CYAN)
            else:
                btn.config(bg=BORDER, fg=TEXT_DIM)
        self._refresh_stats_win()

    @staticmethod
    def _add_months(ref, n):
        """Suma n meses sin desbordar el dia (31 ene -> 28 feb)."""
        m = ref.month - 1 + n
        y, m = ref.year + m // 12, m % 12 + 1
        d = min(ref.day, calendar.monthrange(y, m)[1])
        return ref.replace(year=y, month=m, day=d)

    def _stats_at_present(self):
        """True si el periodo visible ya es el actual (no se puede avanzar)."""
        try:
            p, ref = self._stats_period, self._stats_ref
            now = datetime.now()
            return self._period_bounds(p, ref)[0] >= self._period_bounds(p, now)[0]
        except Exception:
            return True

    def _stats_at_first(self):
        """True si ya se muestra el periodo con los datos mas antiguos."""
        try:
            first = self._stats_store.earliest()
            if first is None:
                return True
            p, ref = self._stats_period, self._stats_ref
            start, end, _ = self._period_bounds(p, ref)
            return start <= first < end
        except Exception:
            return True

    def _stats_step(self, delta):
        """Avanza/retrocede el periodo visible entre el inicio y el presente."""
        try:
            p, ref = self._stats_period, self._stats_ref
            if p == "day":
                cand = ref + timedelta(days=delta)
            elif p == "week":
                cand = ref + timedelta(weeks=delta)
            elif p == "month":
                cand = self._add_months(ref, delta)
            else:
                cand = self._add_months(ref, 12 * delta)
            now = datetime.now()
            if self._period_bounds(p, cand)[0] > self._period_bounds(p, now)[0]:
                return
            first = self._stats_store.earliest()
            if first is not None and self._period_bounds(p, cand)[1] <= first:
                return
            self._stats_ref = cand
        except Exception:
            pass
        self._refresh_stats_win()

    def _refresh_stats_win(self):
        if self._page != "stats" or not self._stats_built:
            return
        try:
            data = self._stats_for(self._stats_period, ref=self._stats_ref)
            self._stats_period_lbl.config(text=data["label"])
            try:
                self._stats_next.config(
                    fg=BORDER if self._stats_at_present() else TEXT_DIM)
                self._stats_prev.config(
                    fg=BORDER if self._stats_at_first() else TEXT_DIM)
            except Exception:
                pass
            vals = self._stats_values
            vals["matches"].config(text=str(data["matches"]))
            vals["activations"].config(text=str(data["activations"]))
            vals["time"].config(text=self._fmt_duration(data["seconds"]))
            vals["avg_act"].config(text=f"{data['avg_per_activation']:.1f}")
            vals["avg_sess"].config(text=self._fmt_duration(data["avg_session"]))
            vals["live"].config(text=self._fmt_duration(data["live"])
                                if data["live"] > 0 else "—")
        except Exception:
            pass

    def _stats_tick(self):
        if self._page != "stats":
            self._stats_tick_on = False
            return
        try:
            if not self.root.winfo_exists():
                self._stats_tick_on = False
                return
        except Exception:
            self._stats_tick_on = False
            return
        self._refresh_stats_win()
        self.root.after(1000, self._stats_tick)

    def _make_slider(self, parent, label, var_name, lbl_name,
                     from_, to, resolution, default, fmt):
        row = tk.Frame(parent, bg=CARD)
        row.pack(fill="x", padx=16, pady=(0, 2))

        tk.Label(row, text=label, font=("Cascadia Code", 10),
                 fg=TEXT, bg=CARD).pack(side="left")

        val = getattr(self, var_name, None)
        if val is None:
            val = tk.DoubleVar(value=default)
            setattr(self, var_name, val)

        val_lbl = tk.Label(row, text=fmt(val.get()),
                           font=("Cascadia Code", 10, "bold"),
                           fg=CYAN, bg=CARD, width=5)
        val_lbl.pack(side="right")
        setattr(self, lbl_name, val_lbl)

        def on_change(v):
            val_lbl.config(text=fmt(float(v)))
            if var_name == "delay_val":
                self.bot.delay = float(v)
            else:
                self.bot.threshold = float(v)
            self._schedule_save_config()

        scale = tk.Scale(
            parent, from_=from_, to=to, resolution=resolution,
            orient="horizontal", variable=val,
            bg=CARD, fg=TEXT, troughcolor=BORDER,
            activebackground=CYAN, highlightthickness=0,
            showvalue=False, command=on_change,
            sliderrelief="flat", sliderlength=14
        )
        scale.pack(fill="x", padx=16, pady=(0, 8))

    # ──────────────────────────────────────────
    # Acciones
    # ──────────────────────────────────────────

    def _toggle_log(self):
        self._set_log_visible(not self._log_visible)

    def _set_log_visible(self, visible, save=True):
        """Muestra/oculta el registro y compacta la ventana (solo en home)."""
        self._log_visible = visible
        if getattr(self, "_page", "home") != "home":
            if save:
                self._save_config()
            return
        try:
            self.root.update_idletasks()
            if visible:
                self.log_card.pack(fill="both", expand=True, padx=24, pady=(0, 20))
                self.root.update_idletasks()
                self.root.geometry(f"390x{self._win_h_full or 560}")
                self.log_toggle_btn.set_active(True)
            else:
                cur = self.root.winfo_height()
                if cur > 200:
                    self._win_h_full = cur
                self.log_card.pack_forget()
                self.root.update_idletasks()
                self.root.geometry(f"390x{self.root.winfo_reqheight()}")
                self.log_toggle_btn.set_active(False)
        except Exception:
            pass
        if save:
            self._save_config()

    def _toggle(self):
        if self.bot_active:
            self.bot.stop()
            self.bot_active = False
            self._join_bot_thread(timeout=2.0)
            self._close_session()
            self._update_status(False)
        else:
            # Evitar dos loops concurrentes si un hilo viejo aún termina.
            self._join_bot_thread(timeout=2.0)
            self.bot_active = True
            self._session_start = datetime.now()
            self._stats["activations"].append(self._session_start.isoformat())
            self._save_stats()
            self._update_status(True)
            self.bot.delay = self.delay_val.get()
            self.bot.threshold = self.thresh_val.get()
            self.bot.auto_deactivate = self.auto_deactivate_var.get()
            self.bot_thread = threading.Thread(target=self.bot.start, daemon=True)
            self.bot_thread.start()
        self._refresh_tray_menu()

    def _join_bot_thread(self, timeout=2.0):
        """Espera al hilo del bot sin bloquear indefinidamente la UI."""
        thread, self.bot_thread = self.bot_thread, None
        try:
            if thread is not None and thread.is_alive():
                thread.join(timeout=timeout)
            # Conservar referencia solo si sigue vivo (evita hilos zombies).
            if thread is not None and thread.is_alive():
                self.bot_thread = thread
        except Exception:
            pass

    def _calibrate(self, _=None):
        if self.bot_active:
            self._log(t("calib_busy"), tag="warn")
            return
        self._log(t("calib_started"), tag="warn")
        threading.Thread(
            target=lambda: self.bot.capture_template(),
            daemon=True
        ).start()

    def _update_status(self, active: bool):
        self.toggle_btn.set_state(active)
        self.dot.set_active(active)
        if active:
            self.status_lbl.config(text=t("status_active"), fg=GREEN)
        else:
            self.status_lbl.config(text=t("status_idle"), fg=RED)
        self._apply_status_icons(active)
        self._refresh_tray_menu()

    def _on_partida_aceptada(self, auto_deactivated=True):
        self._stats["matches"].append(datetime.now().isoformat())
        self._save_stats()
        def _update():
            if auto_deactivated:
                self.bot_active = False
                self._update_status(False)
                self._close_session()
                self._log(t("accepted_auto"))
            else:
                self._log(t("accepted_keep"))
        self.root.after(0, _update)

    # ──────────────────────────────────────────
    # Log
    # ──────────────────────────────────────────

    _LOG_TAGS = ("info", "success", "warn", "error")

    def _log(self, message: str, tag="info"):
        """Escribe un mensaje en el log (thread-safe) con nivel explícito."""
        if tag not in self._LOG_TAGS:
            tag = "info"

        timestamp = time.strftime("%H:%M:%S")
        line = f"[{timestamp}] {message}\n"

        def _write():
            self.log_box.config(state="normal")
            self.log_box.insert("end", line, tag)
            try:
                total = int(self.log_box.index("end-1c").split(".")[0])
                if total > _MAX_LOG_LINES:
                    self.log_box.delete("1.0", f"{total - _MAX_LOG_LINES}.0")
            except Exception:
                pass
            self.log_box.see("end")
            self.log_box.config(state="disabled")

        # Si se llama desde otro hilo
        try:
            self.root.after(0, _write)
        except Exception:
            pass

    # ──────────────────────────────────────────
    # Utilidades
    # ──────────────────────────────────────────

    def _center_window(self, w, h):
        self.root.update_idletasks()
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 2
        self.root.geometry(f"{w}x{h}+{x}+{y}")

    # ──────────────────────────────────────────
    # Configuración persistente (config.json)
    # ──────────────────────────────────────────

    def _load_config(self):
        """Lee config.json con valores validados (delega en config_store)."""
        return load_config(self._config_path)

    def _schedule_save_config(self, delay_ms=400):
        """Debounce de guardado para sliders (evita I/O en cada tick)."""
        try:
            if self._save_cfg_job is not None:
                self.root.after_cancel(self._save_cfg_job)
        except Exception:
            pass
        try:
            self._save_cfg_job = self.root.after(delay_ms, self._save_config_now)
        except Exception:
            pass

    def _save_config_now(self):
        self._save_cfg_job = None
        self._save_config()

    def _save_config(self):
        """Guarda los ajustes actuales en config.json (delega en config_store)."""
        try:
            save_config(
                self._config_path,
                delay=float(self.delay_val.get()),
                threshold=float(self.thresh_val.get()),
                auto_deactivate=bool(self.auto_deactivate_var.get()),
                close_to_tray=bool(self.close_to_tray_var.get()),
                log_visible=bool(getattr(self, "_log_visible", True)),
                pos=list(getattr(self, "_win_pos", None) or []) or None,
                lang=get_language(),
            )
        except Exception:
            pass

    # ──────────────────────────────────────────
    # Estadísticas de uso (stats.json) — delegan en stats_store.StatsStore
    # ──────────────────────────────────────────

    _MESES = StatsStore.MESES

    def _load_stats(self):
        """Recarga stats.json en el store y devuelve el dict (compat)."""
        self._stats_store.load()
        self._stats = self._stats_store.data
        return self._stats

    def _save_stats(self):
        """Guarda los eventos de uso en stats.json (atómico + podado)."""
        self._stats_store.save()

    def _prune_stats(self, limit=MAX_STATS_EVENTS):
        """Limita el crecimiento sin cota: conserva solo los últimos N eventos."""
        self._stats_store.prune(limit)
        self._stats = self._stats_store.data

    def _close_session(self):
        """Cierra la sesión activa actual y la persiste."""
        if self._session_start is None:
            return
        try:
            self._stats_store.close_session(self._session_start, datetime.now())
            self._save_stats()
        except Exception:
            pass
        finally:
            self._session_start = None

    @staticmethod
    def _parse_ts(value):
        return StatsStore.parse_ts(value)

    @classmethod
    def _period_bounds(cls, period, ref=None):
        """Devuelve (inicio, fin, etiqueta) del periodo calendario que contiene a ref."""
        return StatsStore.period_bounds(period, ref)

    def _stats_for(self, period, ref=None):
        """Agrega eventos del periodo visible (delega en el store)."""
        live_start = self._session_start if self.bot_active else None
        return self._stats_store.stats_for(period, ref=ref, live_start=live_start)

    @staticmethod
    def _fmt_duration(seconds):
        """Formatea segundos como '2 h 15 min', '45 min 10 s' o '35 s'."""
        return StatsStore.fmt_duration(seconds)

    def _apply_frameless_style(self, window=None):
        """Mantiene el icono en la barra de tareas y esquinas redondeadas en Win11."""
        target = window if window is not None else self.root
        is_main = target is self.root
        try:
            hwnd = ctypes.windll.user32.GetParent(target.winfo_id())
            # Esquinas redondeadas (Windows 11)
            try:
                DWMWA_WINDOW_CORNER_PREFERENCE = 33
                pref = ctypes.c_int(2)  # 2 = redondeadas
                ctypes.windll.dwmapi.DwmSetWindowAttribute(
                    hwnd, DWMWA_WINDOW_CORNER_PREFERENCE,
                    ctypes.byref(pref), ctypes.sizeof(pref))
            except Exception:
                pass
            # Conservar icono en barra de tareas con overrideredirect(True)
            # (solo ventana principal; el Toplevel usa transient)
            if is_main:
                GWL_EXSTYLE = -20
                WS_EX_APPWINDOW = 0x00040000
                WS_EX_TOOLWINDOW = 0x00000080
                style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
                style = (style & ~WS_EX_TOOLWINDOW) | WS_EX_APPWINDOW
                ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)
                # Refrescar para que el cambio de estilo aplique
                SWP_NOMOVE = 0x0002
                SWP_NOSIZE = 0x0001
                SWP_NOZORDER = 0x0004
                SWP_FRAMECHANGED = 0x0020
                ctypes.windll.user32.SetWindowPos(
                    hwnd, 0, 0, 0, 0, 0,
                    SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER | SWP_FRAMECHANGED)
                self.root.withdraw()
                self.root.after(10, self.root.deiconify)
        except Exception:
            pass

    def _start_move(self, event):
        self._drag_x = event.x_root - self.root.winfo_x()
        self._drag_y = event.y_root - self.root.winfo_y()

    def _on_move(self, event):
        self.root.geometry(f"+{event.x_root - self._drag_x}+{event.y_root - self._drag_y}")

    def _restore_pos(self, pos):
        """Restaura la posición guardada (limitada a la pantalla visible)."""
        try:
            if not (isinstance(pos, (list, tuple)) and len(pos) == 2):
                return
            x, y = int(pos[0]), int(pos[1])
            sw = self.root.winfo_screenwidth()
            sh = self.root.winfo_screenheight()
            x = min(max(x, -50), max(0, sw - 100))
            y = min(max(y, -50), max(0, sh - 100))
            self.root.geometry(f"+{x}+{y}")
            self._win_pos = [x, y]
        except Exception:
            pass

    def _schedule_pos_save(self):
        try:
            if self._pos_job is not None:
                self.root.after_cancel(self._pos_job)
        except Exception:
            pass
        try:
            self._pos_job = self.root.after(1000, self._save_pos_now)
        except Exception:
            pass

    def _save_pos_now(self):
        self._pos_job = None
        try:
            if not self.root.winfo_viewable():
                return
            self._win_pos = [self.root.winfo_x(), self.root.winfo_y()]
        except Exception:
            return
        self._save_config()

    def _close_app(self):
        # Según ajustes: ocultar en bandeja o salir del todo
        if self.close_to_tray_var.get():
            self._hide_to_tray()
        else:
            self._quit_app()

    def _quit_app(self):
        self._save_pos_now()
        try:
            if self.bot_active:
                self.bot.stop()
            self._join_bot_thread(timeout=2.0)
            self._close_session()
        except Exception:
            pass
        try:
            if self._tray is not None:
                self._tray.stop()
        except Exception:
            pass
        try:
            self.root.destroy()
        except Exception:
            pass

    def _restart_app(self):
        """Reinicia la app (aplica cambio de idioma, conserva instancia única)."""
        try:
            if self.bot_active:
                self.bot.stop()
            self._join_bot_thread(timeout=2.0)
            self._close_session()
        except Exception:
            pass
        try:
            if self._tray is not None:
                self._tray.stop()
        except Exception:
            pass
        try:
            if getattr(self, "_instance_sock", None) is not None:
                self._instance_sock.close()
        except Exception:
            pass
        try:
            import subprocess
            if getattr(sys, "frozen", False):
                cmd = [sys.executable]
            else:
                cmd = [sys.executable, os.path.abspath(sys.argv[0])]
            subprocess.Popen(cmd)
        except Exception:
            pass
        try:
            self.root.destroy()
        except Exception:
            pass

    # ──────────────────────────────────────────
    # Bandeja del sistema (delegada en tray.SystemTray)
    # ──────────────────────────────────────────

    def _apply_status_icons(self, active: bool):
        """Punto verde en bandeja + barra de tareas + tooltip según estado."""
        try:
            if self._tray is not None:
                self._tray.apply_status(active)
        except Exception:
            pass

    def _setup_tray(self):
        try:
            from PIL import ImageTk as _ImageTk

            def _set_visible(visible):
                self._window_visible = visible

            self._tray = SystemTray(
                self.root,
                is_active=lambda: self.bot_active,
                on_show=self._show_window,
                on_toggle=self._toggle,
                on_settings=self._open_settings_page,
                on_quit=self._quit_app,
                on_log=self._log,
                on_map=lambda: _set_visible(True),
                on_unmap=lambda: _set_visible(False),
                photo_factory=_ImageTk.PhotoImage,
            )
            self._tray.setup()
        except Exception as e:
            self._log(t("tray_failed", err=e), tag="warn")

    def _refresh_tray_menu(self):
        try:
            if self._tray is not None:
                self._tray.refresh_menu()
        except Exception:
            pass

    def _hide_to_tray(self):
        self.root.withdraw()
        self._window_visible = False
        self._refresh_tray_menu()

    def _show_window(self):
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()
        self._window_visible = True
        self._refresh_tray_menu()

    def start_instance_listener(self, sock):
        """Escucha avisos de segundas instancias para mostrar esta ventana."""
        self._instance_sock = sock

        def _listen():
            while True:
                try:
                    conn, _ = sock.accept()
                    try:
                        conn.recv(16)
                    except Exception:
                        pass
                    try:
                        conn.close()
                    except Exception:
                        pass
                    try:
                        self.root.after(0, self._show_window)
                    except Exception:
                        return
                except Exception:
                    return
        threading.Thread(target=_listen, daemon=True).start()

    def run(self):
        try:
            self.root.protocol("WM_DELETE_WINDOW", self._close_app)
        except Exception:
            pass
        self.root.mainloop()
        try:
            if self._tray is not None:
                self._tray.stop()
        except Exception:
            pass


# ──────────────────────────────────────────────
# ──────────────────────────────────────────────
# Instancia única (una sola copia de la app a la vez)
# ──────────────────────────────────────────────
_SINGLE_INSTANCE_PORT = 51237


def _try_primary_socket():
    """Reserva el puerto local. Si está ocupado, avisa a la instancia
    abierta (para que muestre su ventana) y devuelve None."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # Sin SO_REUSEADDR: en Windows permitiría dos binds simultáneos.
    try:
        sock.bind(("127.0.0.1", _SINGLE_INSTANCE_PORT))
        sock.listen(5)
        return sock
    except OSError:
        try:
            sock.close()
        except Exception:
            pass
        try:
            conn = socket.create_connection(
                ("127.0.0.1", _SINGLE_INSTANCE_PORT), timeout=3)
            try:
                conn.sendall(b"SHOW")
            finally:
                conn.close()
        except Exception:
            pass
        return None


if __name__ == "__main__":
    _sock = _try_primary_socket()
    if _sock is None:
        sys.exit(0)
    _app = App()
    _app.start_instance_listener(_sock)
    _app.run()
