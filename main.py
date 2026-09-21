"""
main.py — Interfaz gráfica premium para el bot de auto-aceptación de LoL
"""

import tkinter as tk
from tkinter import font as tkfont
import threading
import time
import math
import os
import sys
import json
import ctypes
from datetime import datetime, timedelta
from PIL import Image, ImageDraw, ImageTk
import pystray
from pystray import MenuItem as TrayItem, Menu as TrayMenu
from bot import LoLAutoAccept

# Identificador de aplicación para que Windows muestre el icono propio en la barra de tareas
try:
    myappid = "lol.autoaccept.bot.app.1.0"
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
except Exception:
    pass


def _bundled_path(*parts):
    """Ruta a un recurso empaquetado (funciona en .py y en .exe de PyInstaller)."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, *parts)
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), *parts)


def _user_data_dir():
    """Carpeta escribible para config.json/stats.json (junto al .exe si está congelado)."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


_MAX_LOG_LINES = 500
_MAX_STATS_EVENTS = 5000


def _atomic_write_json(path, data):
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


def _load_version():
    """Lee la versión desde version.txt (empaquetado en el .exe)."""
    try:
        with open(_bundled_path("version.txt"), "r", encoding="utf-8") as f:
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

    def __init__(self, parent, text_on="ACTIVAR BOT", text_off="DETENER BOT",
                 command=None, **kwargs):
        super().__init__(parent, width=230, height=58,
                         bg=BG, highlightthickness=0, cursor="hand2", **kwargs)
        self.text_on = text_on
        self.text_off = text_off
        self.command = command
        self.is_on = False
        self._draw()
        self.bind("<Button-1>", self._on_click)
        self.bind("<Enter>", self._on_hover)
        self.bind("<Leave>", self._on_leave)
        self._hovered = False

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
        self._draw(self._hovered)

    def _on_click(self, _):
        if self.command:
            self.command()

    def _on_hover(self, _):
        self._hovered = True
        self._draw(hover=True)

    def _on_leave(self, _):
        self._hovered = False
        self._draw(hover=False)


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
        import math
        pts = []
        for i in range(6):
            angle = math.radians(60 * i - 30)
            pts.extend([cx + r * math.cos(angle), cy + r * math.sin(angle)])
        return pts


class Divider(tk.Frame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg=BORDER, height=1, **kwargs)


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
        self.base_dir = _user_data_dir()
        self._config_path = os.path.join(self.base_dir, "config.json")

        self._center_window(390, 560)
        self._apply_frameless_style()

        # Configurar icono de ventana y barra de tareas (nuevo icono primero)
        ico_path = _bundled_path("app_icon.ico")
        logo_path = None
        for candidate in (_bundled_path("app_icon.png"),
                          _bundled_path("templates", "logo.png")):
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
        self.bot_active = False
        self.bot_thread = None
        self._log_visible = bool(saved.get("log_visible", True))
        self._win_h_full = 560
        self.delay_val = tk.DoubleVar(value=saved["delay"])
        self.thresh_val = tk.DoubleVar(value=saved["threshold"])
        self.auto_deactivate_var = tk.BooleanVar(value=saved["auto_deactivate"])
        self.close_to_tray_var = tk.BooleanVar(value=saved["close_to_tray"])
        self._settings_win = None
        self._tray_icon = None
        self._window_visible = True
        # Estadísticas de uso (persistentes en stats.json)
        self._stats_path = os.path.join(self.base_dir, "stats.json")
        self._stats = self._load_stats()
        self._session_start = None
        self._stats_win = None
        self._stats_period = "day"
        # Variantes del icono según estado (normal / activo con punto verde)
        self._tray_img_off = None
        self._tray_img_on = None
        self._taskbar_photos_off = []
        self._taskbar_photos_on = []

        self.bot = LoLAutoAccept(
            log_callback=self._log,
            accepted_callback=self._on_partida_aceptada
        )

        self._build_ui()
        self._setup_tray()
        self._set_log_visible(self._log_visible, save=False)

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
        tb_title.bind("<ButtonPress-1>", self._start_move)
        tb_title.bind("<B1-Motion>", self._on_move)

        # Botones arriba a la derecha: Ajustes y Cerrar
        tb_close = tk.Label(titlebar, text="✕", font=("Segoe UI Symbol", 10, "bold"),
                            fg=TEXT_DIM, bg=BG, cursor="hand2", width=4)
        tb_close.pack(side="right", fill="y")
        tb_close.bind("<Button-1>", lambda _: self._close_app())
        tb_close.bind("<Enter>", lambda _: tb_close.config(bg=RED, fg=WHITE))
        tb_close.bind("<Leave>", lambda _: tb_close.config(bg=BG, fg=TEXT_DIM))

        tb_cfg = tk.Label(titlebar, text="⚙", font=("Segoe UI Symbol", 11),
                          fg=TEXT_DIM, bg=BG, cursor="hand2", width=4)
        tb_cfg.pack(side="right", fill="y")
        tb_cfg.bind("<Button-1>", self._open_settings)
        tb_cfg.bind("<Enter>", lambda _: tb_cfg.config(bg=BORDER, fg=GOLD))
        tb_cfg.bind("<Leave>", lambda _: tb_cfg.config(bg=BG, fg=TEXT_DIM))

        tb_stats = tk.Label(titlebar, text="📊", font=("Cascadia Code", 10),
                            fg=TEXT_DIM, bg=BG, cursor="hand2", width=4)
        tb_stats.pack(side="right", fill="y")
        tb_stats.bind("<Button-1>", self._open_stats)
        tb_stats.bind("<Enter>", lambda _: tb_stats.config(bg=BORDER, fg=CYAN))
        tb_stats.bind("<Leave>", lambda _: tb_stats.config(bg=BG, fg=TEXT_DIM))

        self.tb_log_btn = tk.Label(titlebar, text="📝", font=("Cascadia Code", 10),
                                   fg=TEXT_DIM, bg=BG, cursor="hand2", width=4)
        self.tb_log_btn.pack(side="right", fill="y")
        self.tb_log_btn.bind("<Button-1>", lambda _: self._toggle_log())
        self.tb_log_btn.bind("<Enter>", lambda _: self.tb_log_btn.config(bg=BORDER, fg=GREEN))
        self.tb_log_btn.bind("<Leave>", lambda _: self.tb_log_btn.config(
            bg=BG, fg=GREEN if self._log_visible else TEXT_DIM))

        # ── Header ──────────────────────────────
        header = tk.Frame(root, bg=BG)
        header.pack(fill="x", padx=24, pady=(10, 10))

        # Logo de la app (nuevo icono primero)
        logo_loaded = False
        for logo_path in (_bundled_path("app_icon.png"),
                          _bundled_path("templates", "logo.png")):
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

        self.status_lbl = tk.Label(left, text="INACTIVO",
                                   font=("Cascadia Code", 11, "bold"),
                                   fg=RED, bg=CARD)
        self.status_lbl.pack(side="left", padx=(8, 0))

        # ── Botón toggle ─────────────────────────
        btn_frame = tk.Frame(root, bg=BG)
        btn_frame.pack(pady=(16, 20))

        self.toggle_btn = GlowButton(btn_frame, command=self._toggle)
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

        tk.Label(log_card, text="REGISTRO",
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

        self._log("Sistema iniciado. Presiona ACTIVAR para comenzar.")

    # ──────────────────────────────────────────
    # Menú de Configuración Separado
    # ──────────────────────────────────────────

    def _open_settings(self, _=None):
        if self._settings_win is not None and self._settings_win.winfo_exists():
            self._settings_win.lift()
            self._settings_win.focus_force()
            return

        win = tk.Toplevel(self.root)
        self._settings_win = win
        win.title("Ajustes - LoL Auto Queue")
        win.geometry("350x730")
        win.resizable(False, False)
        win.configure(bg=BG)
        win.overrideredirect(True)
        win.transient(self.root)

        # Centrar sobre la ventana principal
        self.root.update_idletasks()
        rx = self.root.winfo_x()
        ry = self.root.winfo_y()
        rw = self.root.winfo_width()
        rh = self.root.winfo_height()
        x = rx + (rw - 350) // 2
        y = ry + (rh - 730) // 2
        win.geometry(f"350x730+{max(0, x)}+{max(0, y)}")

        self._apply_frameless_style(win)

        # Arrastre de la ventana de ajustes
        drag = {"x": 0, "y": 0}

        def _s_start_move(event):
            drag["x"] = event.x_root - win.winfo_x()
            drag["y"] = event.y_root - win.winfo_y()

        def _s_on_move(event):
            win.geometry(f"+{event.x_root - drag['x']}+{event.y_root - drag['y']}")

        # ── Barra de título personalizada ──
        s_titlebar = tk.Frame(win, bg=BG, height=36)
        s_titlebar.pack(fill="x", side="top")
        s_titlebar.pack_propagate(False)
        s_titlebar.bind("<ButtonPress-1>", _s_start_move)
        s_titlebar.bind("<B1-Motion>", _s_on_move)

        s_tb_title = tk.Label(s_titlebar, text="Ajustes",
                              font=("Cascadia Code", 9), fg=TEXT_DIM, bg=BG)
        s_tb_title.pack(side="left", padx=12)
        s_tb_title.bind("<ButtonPress-1>", _s_start_move)
        s_tb_title.bind("<B1-Motion>", _s_on_move)

        s_tb_close = tk.Label(s_titlebar, text="✕", font=("Segoe UI Symbol", 10, "bold"),
                              fg=TEXT_DIM, bg=BG, cursor="hand2", width=4)
        s_tb_close.pack(side="right", fill="y")
        s_tb_close.bind("<Button-1>", lambda _: win.destroy())
        s_tb_close.bind("<Enter>", lambda _: s_tb_close.config(bg=RED, fg=WHITE))
        s_tb_close.bind("<Leave>", lambda _: s_tb_close.config(bg=BG, fg=TEXT_DIM))

        # Icono si existe
        ico_path = _bundled_path("app_icon.ico")
        if os.path.exists(ico_path):
            try:
                win.iconbitmap(default=ico_path)
            except Exception:
                pass

        # Encabezado de Ajustes
        s_header = tk.Frame(win, bg=BG)
        s_header.pack(fill="x", padx=20, pady=(6, 10))

        tk.Label(s_header, text="⚙  AJUSTES", font=("Cascadia Code", 13, "bold"),
                 fg=GOLD, bg=BG).pack(side="left")

        Divider(win).pack(fill="x", padx=20, pady=(0, 14))

        # Tarjeta 1: Ajustes de detección (sliders)
        cfg_card = tk.Frame(win, bg=CARD)
        cfg_card.pack(fill="x", padx=20, pady=0)

        tk.Label(cfg_card, text="DETECCIÓN Y TIEMPOS",
                 font=("Cascadia Code", 9, "bold"), fg=TEXT_DIM, bg=CARD
                 ).pack(anchor="w", padx=16, pady=(12, 8))

        # Slider Delay
        self._make_slider(cfg_card, "Delay al aceptar", "delay_val", "delay_lbl",
                          from_=0.1, to=3.0, resolution=0.1, default=0.5,
                          fmt=lambda v: f"{v:.1f}s")

        # Slider Umbral
        self._make_slider(cfg_card, "Umbral de detección", "thresh_val", "thresh_lbl",
                          from_=0.50, to=0.99, resolution=0.01, default=0.80,
                          fmt=lambda v: f"{int(v*100)}%")

        # Tarjeta 2: Comportamiento tras aceptar
        beh_card = tk.Frame(win, bg=CARD)
        beh_card.pack(fill="x", padx=20, pady=(10, 0))

        tk.Label(beh_card, text="AL ACEPTAR PARTIDA",
                 font=("Cascadia Code", 9, "bold"), fg=TEXT_DIM, bg=CARD
                 ).pack(anchor="w", padx=16, pady=(12, 8))

        beh_btns_frame = tk.Frame(beh_card, bg=CARD)
        beh_btns_frame.pack(fill="x", padx=16, pady=(0, 8))

        btn_deact = tk.Label(beh_btns_frame, text="🔒 Desactivar",
                             font=("Cascadia Code", 10, "bold"), cursor="hand2",
                             pady=7, padx=8)
        btn_deact.pack(side="left", fill="x", expand=True, padx=(0, 4))

        btn_keep = tk.Label(beh_btns_frame, text="🔄 Mantener activo",
                            font=("Cascadia Code", 10, "bold"), cursor="hand2",
                            pady=7, padx=8)
        btn_keep.pack(side="right", fill="x", expand=True, padx=(4, 0))

        beh_desc = tk.Label(beh_card, text="", font=("Cascadia Code", 9),
                            fg=TEXT_DIM, bg=CARD, wraplength=275, justify="left")
        beh_desc.pack(anchor="w", padx=16, pady=(0, 12))

        def update_beh_ui():
            if self.auto_deactivate_var.get():
                btn_deact.config(bg="#152636", fg=CYAN)
                btn_keep.config(bg=BORDER, fg=TEXT_DIM)
                beh_desc.config(text="El bot se apaga al aceptar. Deberás volver a activarlo para la siguiente cola.")
            else:
                btn_deact.config(bg=BORDER, fg=TEXT_DIM)
                btn_keep.config(bg="#2E2410", fg=GOLD)
                beh_desc.config(text="El bot sigue buscando por si alguien cancela o rechaza la partida actual.")

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
        tpl_card = tk.Frame(win, bg=CARD)
        tpl_card.pack(fill="x", padx=20, pady=10)

        tk.Label(tpl_card, text="TEMPLATE DE RECONOCIMIENTO",
                 font=("Cascadia Code", 9, "bold"), fg=TEXT_DIM, bg=CARD
                 ).pack(anchor="w", padx=16, pady=(12, 4))

        tk.Label(tpl_card, text="Si cambias de resolución de pantalla, puedes volver a capturar el botón.",
                 font=("Cascadia Code", 9), fg=TEXT_DIM, bg=CARD, wraplength=275, justify="left"
                 ).pack(anchor="w", padx=16, pady=(0, 8))

        cal_btn = tk.Label(tpl_card,
                           text="  📸  Capturar Nuevo Template  ",
                           font=("Cascadia Code", 10, "bold"), fg=CYAN, bg=BORDER,
                           cursor="hand2", pady=7, padx=10)
        cal_btn.pack(padx=16, pady=(0, 14), anchor="w")
        cal_btn.bind("<Button-1>", lambda e: (win.destroy(), self._calibrate()))
        cal_btn.bind("<Enter>", lambda _: cal_btn.config(bg="#2D333B", fg=WHITE))
        cal_btn.bind("<Leave>", lambda _: cal_btn.config(bg=BORDER, fg=CYAN))

        # Tarjeta 4: Comportamiento al cerrar la app
        close_card = tk.Frame(win, bg=CARD)
        close_card.pack(fill="x", padx=20, pady=(0, 10))

        tk.Label(close_card, text="AL CERRAR LA APP",
                 font=("Cascadia Code", 9, "bold"), fg=TEXT_DIM, bg=CARD
                 ).pack(anchor="w", padx=16, pady=(12, 8))

        close_btns_frame = tk.Frame(close_card, bg=CARD)
        close_btns_frame.pack(fill="x", padx=16, pady=(0, 8))

        btn_quit = tk.Label(close_btns_frame, text="⏻ Salir",
                            font=("Cascadia Code", 10, "bold"), cursor="hand2",
                            pady=7, padx=8)
        btn_quit.pack(side="left", fill="x", expand=True, padx=(0, 4))

        btn_tray = tk.Label(close_btns_frame, text="📥 Bandeja",
                            font=("Cascadia Code", 10, "bold"), cursor="hand2",
                            pady=7, padx=8)
        btn_tray.pack(side="right", fill="x", expand=True, padx=(4, 0))

        close_desc = tk.Label(close_card, text="", font=("Cascadia Code", 9),
                              fg=TEXT_DIM, bg=CARD, wraplength=275, justify="left")
        close_desc.pack(anchor="w", padx=16, pady=(0, 12))

        def update_close_ui():
            if self.close_to_tray_var.get():
                btn_tray.config(bg="#152636", fg=CYAN)
                btn_quit.config(bg=BORDER, fg=TEXT_DIM)
                close_desc.config(text="La ✕ oculta la ventana y la app sigue en los iconos de Windows.")
            else:
                btn_tray.config(bg=BORDER, fg=TEXT_DIM)
                btn_quit.config(bg="#2E2410", fg=GOLD)
                close_desc.config(text="La ✕ detiene el bot y cierra la app por completo.")

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

        # La ventana recién creada (frameless + transient) puede abrirse
        # detrás de la principal: traerla al frente ya en el primer clic.
        win.update_idletasks()
        win.deiconify()
        win.lift()
        win.focus_force()
        win.after(10, lambda: (win.lift(), win.focus_force())
                 if win.winfo_exists() else None)

    # ──────────────────────────────────────────
    # Ventana de Estadísticas
    # ──────────────────────────────────────────

    def _open_stats(self, _=None):
        if self._stats_win is not None and self._stats_win.winfo_exists():
            self._stats_win.lift()
            self._stats_win.focus_force()
            return

        win = tk.Toplevel(self.root)
        self._stats_win = win
        win.title("Estadísticas - LoL Auto Queue")
        win.resizable(False, False)
        win.configure(bg=BG)
        win.overrideredirect(True)
        win.transient(self.root)

        W, H = 350, 600
        self.root.update_idletasks()
        rx, ry = self.root.winfo_x(), self.root.winfo_y()
        rw, rh = self.root.winfo_width(), self.root.winfo_height()
        x = rx + (rw - W) // 2
        y = ry + (rh - H) // 2
        win.geometry(f"{W}x{H}+{max(0, x)}+{max(0, y)}")

        self._apply_frameless_style(win)

        drag = {"x": 0, "y": 0}

        def _s_start_move(event):
            drag["x"] = event.x_root - win.winfo_x()
            drag["y"] = event.y_root - win.winfo_y()

        def _s_on_move(event):
            win.geometry(f"+{event.x_root - drag['x']}+{event.y_root - drag['y']}")

        # ── Barra de título personalizada ──
        titlebar = tk.Frame(win, bg=BG, height=36)
        titlebar.pack(fill="x", side="top")
        titlebar.pack_propagate(False)
        titlebar.bind("<ButtonPress-1>", _s_start_move)
        titlebar.bind("<B1-Motion>", _s_on_move)

        tb_title = tk.Label(titlebar, text="Estadísticas",
                            font=("Cascadia Code", 9), fg=TEXT_DIM, bg=BG)
        tb_title.pack(side="left", padx=12)
        tb_title.bind("<ButtonPress-1>", _s_start_move)
        tb_title.bind("<B1-Motion>", _s_on_move)

        tb_close = tk.Label(titlebar, text="✕", font=("Segoe UI Symbol", 10, "bold"),
                            fg=TEXT_DIM, bg=BG, cursor="hand2", width=4)
        tb_close.pack(side="right", fill="y")
        tb_close.bind("<Button-1>", lambda _: win.destroy())
        tb_close.bind("<Enter>", lambda _: tb_close.config(bg=RED, fg=WHITE))
        tb_close.bind("<Leave>", lambda _: tb_close.config(bg=BG, fg=TEXT_DIM))

        # Encabezado
        header = tk.Frame(win, bg=BG)
        header.pack(fill="x", padx=20, pady=(6, 4))
        tk.Label(header, text="📊  ESTADÍSTICAS", font=("Cascadia Code", 12, "bold"),
                 fg=GOLD, bg=BG).pack(side="left")
        self._stats_period_lbl = tk.Label(header, text="", font=("Cascadia Code", 9),
                                          fg=TEXT_DIM, bg=BG)
        self._stats_period_lbl.pack(side="right")

        Divider(win).pack(fill="x", padx=20, pady=(6, 12))

        # ── Selector de periodo ──
        per_card = tk.Frame(win, bg=CARD)
        per_card.pack(fill="x", padx=20, pady=0)
        tk.Label(per_card, text="PERIODO",
                 font=("Cascadia Code", 9, "bold"), fg=TEXT_DIM, bg=CARD
                 ).pack(anchor="w", padx=16, pady=(12, 8))

        per_row = tk.Frame(per_card, bg=CARD)
        per_row.pack(fill="x", padx=16, pady=(0, 12))

        self._period_btns = {}
        for key, txt in (("day", "Día"), ("week", "Semana"),
                         ("month", "Mes"), ("year", "Año")):
            btn = tk.Label(per_row, text=txt, font=("Cascadia Code", 9, "bold"),
                           cursor="hand2", pady=7)
            btn.pack(side="left", fill="x", expand=True,
                     padx=(0, 4) if key != "year" else (0, 0))
            btn.bind("<Button-1>", lambda _, k=key: self._select_period(k))
            self._period_btns[key] = btn

        # ── Tarjeta de valores ──
        stats_card = tk.Frame(win, bg=CARD)
        stats_card.pack(fill="x", padx=20, pady=(10, 0))

        self._stats_values = {}
        for key, label, color in (
            ("matches", "🎮  Partidas aceptadas", CYAN),
            ("activations", "▶  Veces activado", WHITE),
            ("time", "⏱  Tiempo activo", GREEN),
            ("avg_act", "📈  Promedio por activación", WHITE),
            ("avg_sess", "⏳  Sesión promedio", WHITE),
            ("live", "🟢  Sesión actual", GREEN),
        ):
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
        reset_btn = tk.Label(win, text="↺  Restablecer estadísticas",
                             font=("Cascadia Code", 9, "bold"), fg=TEXT_DIM, bg=BORDER,
                             cursor="hand2", pady=8)
        reset_btn.pack(fill="x", padx=20, pady=(10, 0))
        reset_state = {"confirm": False}

        def _do_reset(_=None):
            if not reset_state["confirm"]:
                reset_state["confirm"] = True
                reset_btn.config(text="¿Tocar de nuevo para confirmar?", fg=RED)
                win.after(3000, lambda: (reset_state.update(confirm=False),
                                         reset_btn.config(
                                             text="↺  Restablecer estadísticas",
                                             fg=TEXT_DIM))
                          if win.winfo_exists() else None)
                return
            self._stats = {"activations": [], "matches": [], "sessions": []}
            self._save_stats()
            reset_state["confirm"] = False
            reset_btn.config(text="↺  Restablecer estadísticas", fg=TEXT_DIM)
            self._refresh_stats_win()
            self._log("📊 Estadísticas restablecidas.")

        reset_btn.bind("<Button-1>", _do_reset)
        reset_btn.bind("<Enter>", lambda _: reset_btn.config(bg="#2D333B", fg=WHITE)
                       if not reset_state["confirm"] else None)
        reset_btn.bind("<Leave>", lambda _: reset_btn.config(bg=BORDER, fg=TEXT_DIM)
                       if not reset_state["confirm"] else None)

        win.update_idletasks()
        win.deiconify()
        win.lift()
        win.focus_force()
        win.after(10, lambda: (win.lift(), win.focus_force())
                 if win.winfo_exists() else None)

        self._select_period(self._stats_period)
        self._stats_tick(win)

    def _select_period(self, period):
        self._stats_period = period
        for key, btn in getattr(self, "_period_btns", {}).items():
            if key == period:
                btn.config(bg="#152636", fg=CYAN)
            else:
                btn.config(bg=BORDER, fg=TEXT_DIM)
        self._refresh_stats_win()

    def _refresh_stats_win(self):
        if self._stats_win is None or not self._stats_win.winfo_exists():
            return
        try:
            data = self._stats_for(self._stats_period)
            self._stats_period_lbl.config(text=data["label"])
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

    def _stats_tick(self, win):
        try:
            if not win.winfo_exists():
                return
        except Exception:
            return
        self._refresh_stats_win()
        win.after(1000, lambda: self._stats_tick(win))

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
            self._save_config()

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
        """Muestra/oculta el registro y compacta la ventana."""
        self._log_visible = visible
        try:
            self.root.update_idletasks()
            if visible:
                self.log_card.pack(fill="both", expand=True, padx=24, pady=(0, 20))
                self.root.update_idletasks()
                self.root.geometry(f"390x{self._win_h_full or 560}")
                self.tb_log_btn.config(fg=GREEN)
            else:
                cur = self.root.winfo_height()
                if cur > 200:
                    self._win_h_full = cur
                self.log_card.pack_forget()
                self.root.update_idletasks()
                self.root.geometry(f"390x{self.root.winfo_reqheight()}")
                self.tb_log_btn.config(fg=TEXT_DIM)
        except Exception:
            pass
        if save:
            self._save_config()

    def _toggle(self):
        if self.bot_active:
            self.bot.stop()
            self.bot_active = False
            self._close_session()
            self._update_status(False)
        else:
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

    def _calibrate(self, _=None):
        if self.bot_active:
            self._log("⚠️ Detén el bot antes de calibrar.", tag="warn")
            return
        self._log("📸 Calibración iniciada — 3 segundos para mostrar el popup...", tag="warn")
        threading.Thread(
            target=lambda: self.bot.capture_template(),
            daemon=True
        ).start()

    def _update_status(self, active: bool):
        self.toggle_btn.set_state(active)
        self.dot.set_active(active)
        if active:
            self.status_lbl.config(text="ACTIVO", fg=GREEN)
        else:
            self.status_lbl.config(text="INACTIVO", fg=RED)
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
                self._log("🔒 Bot desactivado automáticamente tras aceptar.")
            else:
                self._log("🔄 Bot continúa activo por si se cancela la cola.")
        self.root.after(0, _update)

    # ──────────────────────────────────────────
    # Log
    # ──────────────────────────────────────────

    def _log(self, message: str, tag="info"):
        """Escribe un mensaje en el log (thread-safe)."""
        # Detectar tipo de mensaje automáticamente
        if any(x in message for x in ["✅", "🎮", "✅"]):
            tag = "success"
        elif any(x in message for x in ["⚠️", "📸"]):
            tag = "warn"
        elif any(x in message for x in ["❌", "Error"]):
            tag = "error"

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
        """Lee config.json con valores validados; usa defaults si falta o es inválido."""
        cfg = {"delay": 0.5, "threshold": 0.80,
               "auto_deactivate": True, "close_to_tray": True,
               "log_visible": True}
        try:
            with open(self._config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                cfg["delay"] = min(3.0, max(0.1, float(data.get("delay", cfg["delay"]))))
                cfg["threshold"] = min(0.99, max(0.50, float(data.get("threshold", cfg["threshold"]))))
                cfg["auto_deactivate"] = bool(data.get("auto_deactivate", cfg["auto_deactivate"]))
                cfg["close_to_tray"] = bool(data.get("close_to_tray", cfg["close_to_tray"]))
                cfg["log_visible"] = bool(data.get("log_visible", cfg["log_visible"]))
        except Exception:
            pass
        return cfg

    def _save_config(self):
        """Guarda los ajustes actuales en config.json (escritura atómica)."""
        try:
            data = {
                "delay": round(float(self.delay_val.get()), 2),
                "threshold": round(float(self.thresh_val.get()), 2),
                "auto_deactivate": bool(self.auto_deactivate_var.get()),
                "close_to_tray": bool(self.close_to_tray_var.get()),
                "log_visible": bool(getattr(self, "_log_visible", True)),
            }
            _atomic_write_json(self._config_path, data)
        except Exception:
            pass

    # ──────────────────────────────────────────
    # Estadísticas de uso (stats.json)
    # ──────────────────────────────────────────

    _MESES = ("enero", "febrero", "marzo", "abril", "mayo", "junio",
              "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre")

    def _load_stats(self):
        """Lee stats.json; estructura válida o vacía si falta/es inválido."""
        stats = {"activations": [], "matches": [], "sessions": []}
        try:
            with open(self._stats_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                for key in stats:
                    val = data.get(key, [])
                    if isinstance(val, list):
                        stats[key] = val
        except Exception:
            pass
        return stats

    def _save_stats(self):
        """Guarda los eventos de uso en stats.json (atómico + podado)."""
        try:
            self._prune_stats()
            _atomic_write_json(self._stats_path, self._stats)
        except Exception:
            pass

    def _prune_stats(self, limit=_MAX_STATS_EVENTS):
        """Limita el crecimiento sin cota: conserva solo los últimos N eventos."""
        try:
            for key in ("activations", "matches", "sessions"):
                val = self._stats.get(key)
                if isinstance(val, list) and len(val) > limit:
                    self._stats[key] = val[-limit:]
        except Exception:
            pass

    def _close_session(self):
        """Cierra la sesión activa actual y la persiste."""
        if self._session_start is None:
            return
        try:
            end = datetime.now()
            self._stats["sessions"].append({
                "start": self._session_start.isoformat(),
                "end": end.isoformat(),
                "seconds": round((end - self._session_start).total_seconds(), 1),
            })
            self._save_stats()
        except Exception:
            pass
        finally:
            self._session_start = None

    @staticmethod
    def _parse_ts(value):
        try:
            return datetime.fromisoformat(value)
        except Exception:
            return None

    @classmethod
    def _period_bounds(cls, period, ref=None):
        """Devuelve (inicio, fin, etiqueta) del periodo calendario que contiene a ref."""
        ref = ref or datetime.now()
        if period == "week":
            start = datetime(ref.year, ref.month, ref.day) - timedelta(days=ref.weekday())
            end = start + timedelta(days=7)
            label = (f"{start.day} – {end.day - 1} "
                     f"{cls._MESES[start.month - 1]} {start.year}")
        elif period == "month":
            start = datetime(ref.year, ref.month, 1)
            end = datetime(ref.year + (ref.month == 12), ref.month % 12 + 1, 1)
            label = f"{cls._MESES[ref.month - 1]} {ref.year}"
        elif period == "year":
            start = datetime(ref.year, 1, 1)
            end = datetime(ref.year + 1, 1, 1)
            label = str(ref.year)
        else:  # day
            start = datetime(ref.year, ref.month, ref.day)
            end = start + timedelta(days=1)
            label = f"{start.day} {cls._MESES[start.month - 1]} {start.year}"
        return start, end, label

    def _stats_for(self, period):
        """Agrega eventos del periodo: partidas, activaciones y tiempo activo."""
        start, end, label = self._period_bounds(period)
        matches = sum(1 for ts in self._stats["matches"]
                      if (dt := self._parse_ts(ts)) is not None and start <= dt < end)
        activations = sum(1 for ts in self._stats["activations"]
                          if (dt := self._parse_ts(ts)) is not None and start <= dt < end)
        seconds, sessions = 0.0, 0
        for s in self._stats["sessions"]:
            s0 = self._parse_ts(s.get("start", ""))
            s1 = self._parse_ts(s.get("end", ""))
            if s0 is None or s1 is None:
                continue
            overlap = (min(s1, end) - max(s0, start)).total_seconds()
            if overlap > 0:
                seconds += overlap
                sessions += 1
        live = 0.0
        if self.bot_active and self._session_start is not None:
            live = max(0.0, (min(datetime.now(), end) - max(self._session_start, start)
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
    def _fmt_duration(seconds):
        """Formatea segundos como '2 h 15 min', '45 min 10 s' o '35 s'."""
        seconds = int(max(0, seconds))
        h, rem = divmod(seconds, 3600)
        m, s = divmod(rem, 60)
        if h:
            return f"{h} h {m} min" if m else f"{h} h"
        if m:
            return f"{m} min {s} s" if s else f"{m} min"
        return f"{s} s"

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

    def _close_app(self):
        # Según ajustes: ocultar en bandeja o salir del todo
        if self.close_to_tray_var.get():
            self._hide_to_tray()
        else:
            self._quit_app()

    def _quit_app(self):
        try:
            if self.bot_active:
                self.bot.stop()
            self._close_session()
        except Exception:
            pass
        try:
            if self._tray_icon is not None:
                self._tray_icon.stop()
        except Exception:
            pass
        try:
            self.root.destroy()
        except Exception:
            pass

    # ──────────────────────────────────────────
    # Bandeja del sistema (system tray)
    # ──────────────────────────────────────────

    def _base_icon(self):
        """Carga el icono nuevo primero (PIL, RGBA)."""
        for candidate in (
            _bundled_path("app_icon.png"),
            _bundled_path("templates", "logo.png"),
        ):
            if os.path.exists(candidate):
                try:
                    return Image.open(candidate).convert("RGBA")
                except Exception:
                    pass
        return Image.new("RGBA", (256, 256), (200, 155, 60, 255))

    @staticmethod
    def _badged_size(base, size):
        """Variante 'activo': base reescalada a `size` y punto dibujado a ese
        tamaño final (bordes nítidos, sin doble reescalado)."""
        img = base.resize((size, size), Image.Resampling.LANCZOS)
        s = size / 256.0
        margin = max(1, int(round(10 * s)))
        r_out = max(2, int(round(38 * s)))
        r_in = max(1, int(round(29 * s)))
        cx = cy = size - margin - r_out
        draw = ImageDraw.Draw(img)
        draw.ellipse([cx - r_out, cy - r_out, cx + r_out, cy + r_out],
                     fill=(13, 17, 23, 255))
        draw.ellipse([cx - r_in, cy - r_in, cx + r_in, cy + r_in],
                     fill=(0, 230, 118, 255))
        return img

    def _build_status_icons(self):
        """Prepara variantes inactivo/activo a máxima resolución."""
        try:
            base = self._base_icon()  # resolución nativa (523px)
            self._tray_img_off = base.resize((64, 64), Image.Resampling.LANCZOS)
            self._tray_img_on = self._badged_size(base, 64)
            try:
                # Varios tamaños para que Windows no tenga que reescalar
                self._taskbar_photos_off = [
                    ImageTk.PhotoImage(base.resize((s, s), Image.Resampling.LANCZOS))
                    for s in (16, 24, 32, 48)]
                self._taskbar_photos_on = [
                    ImageTk.PhotoImage(self._badged_size(base, s))
                    for s in (16, 24, 32, 48)]
            except Exception:
                pass
        except Exception:
            pass

    def _tray_image(self):
        """Icono para la bandeja (64x64). Usa el icono nuevo primero."""
        if self._tray_img_off is not None:
            return self._tray_img_off
        for candidate in (
            _bundled_path("app_icon.png"),
            _bundled_path("templates", "logo.png"),
        ):
            if os.path.exists(candidate):
                try:
                    img = Image.open(candidate).convert("RGBA")
                    return img.resize((64, 64), Image.Resampling.LANCZOS)
                except Exception:
                    pass
        return Image.new("RGBA", (64, 64), (200, 155, 60, 255))

    def _apply_status_icons(self, active: bool):
        """Punto verde en bandeja + barra de tareas + tooltip según estado.

        Solo se usa iconphoto (nítido). El iconbitmap del .ico se deja fijo
        desde el arranque: intercambiarlo en caliente pixelaba la barra.
        """
        try:
            if self._tray_icon is not None:
                img = self._tray_img_on if active else self._tray_img_off
                if img is not None:
                    self._tray_icon.icon = img
                self._tray_icon.title = (
                    "LoL Auto Queue — ACTIVO" if active
                    else "LoL Auto Queue — INACTIVO")
        except Exception:
            pass
        try:
            photos = self._taskbar_photos_on if active else self._taskbar_photos_off
            if photos:
                self.root.iconphoto(True, *photos)
        except Exception:
            pass

    def _setup_tray(self):
        try:
            self._build_status_icons()
            menu = TrayMenu(
                TrayItem('Mostrar ventana',
                         lambda icon, _: self.root.after(0, self._show_window),
                         default=True, visible=False),
                TrayItem(
                    lambda _: "Desactivar bot" if self.bot_active else "Activar bot",
                    lambda icon, _: self.root.after(0, self._toggle)),
                TrayItem("Abrir configuraciones",
                         lambda icon, _: self.root.after(0, self._open_settings)),
                TrayItem("Cerrar", lambda icon, _: self.root.after(0, self._quit_app)),
            )
            self._tray_icon = pystray.Icon(
                "LoL Auto Queue", self._tray_image(),
                "LoL Auto Queue — INACTIVO", menu)
            threading.Thread(target=self._tray_icon.run, daemon=True).start()
            self.root.bind("<Map>", lambda _: self._on_window_map())
            self.root.bind("<Unmap>", lambda _: self._on_window_unmap())
        except Exception as e:
            self._log(f"⚠️ No se pudo crear el icono de bandeja: {e}", tag="warn")

    def _refresh_tray_menu(self):
        try:
            if self._tray_icon is not None:
                self._tray_icon.update_menu()
        except Exception:
            pass

    def _on_window_map(self):
        self._window_visible = True
        self._refresh_tray_menu()

    def _on_window_unmap(self):
        self._window_visible = False
        self._refresh_tray_menu()

    def _hide_to_tray(self):
        try:
            if self._settings_win is not None and self._settings_win.winfo_exists():
                self._settings_win.withdraw()
        except Exception:
            pass
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
            if self._tray_icon is not None:
                self._tray_icon.stop()
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
    import socket
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
