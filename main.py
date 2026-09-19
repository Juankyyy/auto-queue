"""
main.py — Interfaz gráfica premium para el bot de auto-aceptación de LoL
"""

import tkinter as tk
from tkinter import font as tkfont
import threading
import time
import math
import os
import ctypes
from PIL import Image, ImageTk
from bot import LoLAutoAccept

# Identificador de aplicación para que Windows muestre el icono propio en la barra de tareas
try:
    myappid = "lol.autoaccept.bot.app.1.0"
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
except Exception:
    pass


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
    """Círculo pulsante que indica el estado del bot."""

    def __init__(self, parent, size=14, **kwargs):
        super().__init__(parent, width=size, height=size,
                         bg=CARD, highlightthickness=0, **kwargs)
        self.size = size
        self.active = False
        self._pulse_step = 0
        self._dot = None
        self._draw(RED)

    def _draw(self, color, radius_factor=1.0):
        self.delete("all")
        c = self.size / 2
        r = (self.size / 2 - 2) * radius_factor
        self.create_oval(c - r, c - r, c + r, c + r, fill=color, outline="")

    def set_active(self, active: bool):
        self.active = active
        if active:
            self._animate()
        else:
            self._draw(RED)

    def _animate(self):
        if not self.active:
            return
        self._pulse_step += 0.12
        factor = 0.75 + 0.25 * math.sin(self._pulse_step)
        self._draw(GREEN, radius_factor=factor)
        self.after(50, self._animate)


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
                         font=("Segoe UI", 12, "bold"), fill=text_color)

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
        self.create_text(cx, cy, text="L", font=("Segoe UI", int(size * 0.3), "bold"),
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
        self.root.title("LoL Auto Queue")
        self.root.geometry("390x540")
        self.root.resizable(False, False)
        self.root.configure(bg=BG)
        # Ventana sin decoración nativa de Windows (frameless)
        self.root.overrideredirect(True)
        self._drag_x = 0
        self._drag_y = 0

        self._center_window(390, 540)
        self._apply_frameless_style()

        # Configurar icono de ventana y barra de tareas
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        ico_path = os.path.join(self.base_dir, "app_icon.ico")
        logo_path = os.path.join(self.base_dir, "templates", "logo.png")
        if not os.path.exists(logo_path):
            logo_path = os.path.join(self.base_dir, "app_icon.png")

        if os.path.exists(ico_path):
            try:
                self.root.iconbitmap(default=ico_path)
            except Exception:
                pass

        if os.path.exists(logo_path):
            try:
                self._icon_img = ImageTk.PhotoImage(file=logo_path)
                self.root.iconphoto(True, self._icon_img)
            except Exception:
                pass

        # Estado y variables de configuración
        self.bot_active = False
        self.bot_thread = None
        self.delay_val = tk.DoubleVar(value=0.5)
        self.thresh_val = tk.DoubleVar(value=0.80)
        self.auto_deactivate_var = tk.BooleanVar(value=True)
        self._settings_win = None

        self.bot = LoLAutoAccept(
            log_callback=self._log,
            accepted_callback=self._on_partida_aceptada
        )

        self._build_ui()

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
                            font=("Segoe UI", 8), fg=TEXT_DIM, bg=BG)
        tb_title.pack(side="left", padx=12)
        tb_title.bind("<ButtonPress-1>", self._start_move)
        tb_title.bind("<B1-Motion>", self._on_move)

        # Botones arriba a la derecha: Ajustes, Minimizar y Cerrar
        tb_close = tk.Label(titlebar, text="✕", font=("Segoe UI", 10, "bold"),
                            fg=TEXT_DIM, bg=BG, cursor="hand2", width=4)
        tb_close.pack(side="right", fill="y")
        tb_close.bind("<Button-1>", lambda _: self._close_app())
        tb_close.bind("<Enter>", lambda _: tb_close.config(bg=RED, fg=WHITE))
        tb_close.bind("<Leave>", lambda _: tb_close.config(bg=BG, fg=TEXT_DIM))

        tb_min = tk.Label(titlebar, text="─", font=("Segoe UI", 10),
                          fg=TEXT_DIM, bg=BG, cursor="hand2", width=4)
        tb_min.pack(side="right", fill="y")
        tb_min.bind("<Button-1>", lambda _: root.iconify())
        tb_min.bind("<Enter>", lambda _: tb_min.config(bg=BORDER, fg=WHITE))
        tb_min.bind("<Leave>", lambda _: tb_min.config(bg=BG, fg=TEXT_DIM))

        tb_cfg = tk.Label(titlebar, text="⚙", font=("Segoe UI", 11),
                          fg=TEXT_DIM, bg=BG, cursor="hand2", width=4)
        tb_cfg.pack(side="right", fill="y")
        tb_cfg.bind("<Button-1>", self._open_settings)
        tb_cfg.bind("<Enter>", lambda _: tb_cfg.config(bg=BORDER, fg=GOLD))
        tb_cfg.bind("<Leave>", lambda _: tb_cfg.config(bg=BG, fg=TEXT_DIM))

        # ── Header ──────────────────────────────
        header = tk.Frame(root, bg=BG)
        header.pack(fill="x", padx=24, pady=(10, 10))

        # Logo de la app desde templates/logo.png
        logo_path = os.path.join(self.base_dir, "templates", "logo.png")
        logo_loaded = False
        if os.path.exists(logo_path):
            try:
                pil_logo = Image.open(logo_path).resize((46, 46), Image.Resampling.LANCZOS)
                self.header_logo = ImageTk.PhotoImage(pil_logo)
                logo_lbl = tk.Label(header, image=self.header_logo, bg=BG)
                logo_lbl.pack(side="left")
                logo_loaded = True
            except Exception:
                logo_loaded = False

        if not logo_loaded:
            HexIcon(header, size=46).pack(side="left")

        titles = tk.Frame(header, bg=BG)
        titles.pack(side="left", padx=12)
        tk.Label(titles, text="LoL Auto Queue",
                 font=("Segoe UI", 15, "bold"), fg=GOLD, bg=BG).pack(anchor="w")
        tk.Label(titles, text="Acepta partidas automáticamente",
                 font=("Segoe UI", 9), fg=TEXT_DIM, bg=BG).pack(anchor="w")

        Divider(root).pack(fill="x", padx=24, pady=(0, 0))

        # ── Tarjeta de estado ────────────────────
        status_card = tk.Frame(root, bg=CARD, pady=0)
        status_card.pack(fill="x", padx=24, pady=16)

        left = tk.Frame(status_card, bg=CARD)
        left.pack(side="left", padx=16, pady=14)

        self.dot = AnimatedDot(left, size=12)
        self.dot.pack(side="left")

        self.status_lbl = tk.Label(left, text="INACTIVO",
                                   font=("Segoe UI", 10, "bold"),
                                   fg=RED, bg=CARD)
        self.status_lbl.pack(side="left", padx=(8, 0))

        self.count_lbl = tk.Label(status_card,
                                  text="Partidas aceptadas: 0",
                                  font=("Segoe UI", 9), fg=TEXT_DIM, bg=CARD)
        self.count_lbl.pack(side="right", padx=16)

        # ── Botón toggle ─────────────────────────
        btn_frame = tk.Frame(root, bg=BG)
        btn_frame.pack(pady=16)

        self.toggle_btn = GlowButton(btn_frame, command=self._toggle)
        self.toggle_btn.pack()

        # ── Log ──────────────────────────────────
        log_card = tk.Frame(root, bg=CARD)
        log_card.pack(fill="both", expand=True, padx=24, pady=(8, 20))

        tk.Label(log_card, text="REGISTRO",
                 font=("Segoe UI", 8, "bold"), fg=TEXT_DIM, bg=CARD
                 ).pack(anchor="w", padx=14, pady=(10, 4))

        self.log_box = tk.Text(
            log_card, height=8, bg="#090D12", fg="#3FB950",
            font=("Consolas", 8), relief="flat", state="disabled",
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
        win.geometry("350x546")
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
        y = ry + (rh - 546) // 2
        win.geometry(f"350x546+{max(0, x)}+{max(0, y)}")

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
                              font=("Segoe UI", 8), fg=TEXT_DIM, bg=BG)
        s_tb_title.pack(side="left", padx=12)
        s_tb_title.bind("<ButtonPress-1>", _s_start_move)
        s_tb_title.bind("<B1-Motion>", _s_on_move)

        s_tb_close = tk.Label(s_titlebar, text="✕", font=("Segoe UI", 10, "bold"),
                              fg=TEXT_DIM, bg=BG, cursor="hand2", width=4)
        s_tb_close.pack(side="right", fill="y")
        s_tb_close.bind("<Button-1>", lambda _: win.destroy())
        s_tb_close.bind("<Enter>", lambda _: s_tb_close.config(bg=RED, fg=WHITE))
        s_tb_close.bind("<Leave>", lambda _: s_tb_close.config(bg=BG, fg=TEXT_DIM))

        # Icono si existe
        ico_path = os.path.join(self.base_dir, "app_icon.ico")
        if os.path.exists(ico_path):
            try:
                win.iconbitmap(default=ico_path)
            except Exception:
                pass

        # Encabezado de Ajustes
        s_header = tk.Frame(win, bg=BG)
        s_header.pack(fill="x", padx=20, pady=(6, 10))

        tk.Label(s_header, text="⚙  AJUSTES", font=("Segoe UI", 12, "bold"),
                 fg=GOLD, bg=BG).pack(side="left")

        Divider(win).pack(fill="x", padx=20, pady=(0, 14))

        # Tarjeta 1: Ajustes de detección (sliders)
        cfg_card = tk.Frame(win, bg=CARD)
        cfg_card.pack(fill="x", padx=20, pady=0)

        tk.Label(cfg_card, text="DETECCIÓN Y TIEMPOS",
                 font=("Segoe UI", 8, "bold"), fg=TEXT_DIM, bg=CARD
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
                 font=("Segoe UI", 8, "bold"), fg=TEXT_DIM, bg=CARD
                 ).pack(anchor="w", padx=16, pady=(12, 8))

        beh_btns_frame = tk.Frame(beh_card, bg=CARD)
        beh_btns_frame.pack(fill="x", padx=16, pady=(0, 8))

        btn_deact = tk.Label(beh_btns_frame, text="🔒 Desactivar",
                             font=("Segoe UI", 9, "bold"), cursor="hand2",
                             pady=7, padx=8)
        btn_deact.pack(side="left", fill="x", expand=True, padx=(0, 4))

        btn_keep = tk.Label(beh_btns_frame, text="🔄 Mantener activo",
                            font=("Segoe UI", 9, "bold"), cursor="hand2",
                            pady=7, padx=8)
        btn_keep.pack(side="right", fill="x", expand=True, padx=(4, 0))

        beh_desc = tk.Label(beh_card, text="", font=("Segoe UI", 8),
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

        def select_keep(_=None):
            self.auto_deactivate_var.set(False)
            self.bot.auto_deactivate = False
            update_beh_ui()

        btn_deact.bind("<Button-1>", select_deact)
        btn_keep.bind("<Button-1>", select_keep)
        update_beh_ui()

        # Tarjeta 3: Calibración / template
        tpl_card = tk.Frame(win, bg=CARD)
        tpl_card.pack(fill="x", padx=20, pady=10)

        tk.Label(tpl_card, text="TEMPLATE DE RECONOCIMIENTO",
                 font=("Segoe UI", 8, "bold"), fg=TEXT_DIM, bg=CARD
                 ).pack(anchor="w", padx=16, pady=(12, 4))

        tk.Label(tpl_card, text="Si cambias de resolución de pantalla, puedes volver a capturar el botón.",
                 font=("Segoe UI", 8), fg=TEXT_DIM, bg=CARD, wraplength=275, justify="left"
                 ).pack(anchor="w", padx=16, pady=(0, 8))

        cal_btn = tk.Label(tpl_card,
                           text="  📸  Capturar Nuevo Template  ",
                           font=("Segoe UI", 9, "bold"), fg=CYAN, bg=BORDER,
                           cursor="hand2", pady=7, padx=10)
        cal_btn.pack(padx=16, pady=(0, 14), anchor="w")
        cal_btn.bind("<Button-1>", lambda e: (win.destroy(), self._calibrate()))
        cal_btn.bind("<Enter>", lambda _: cal_btn.config(bg="#2D333B", fg=WHITE))
        cal_btn.bind("<Leave>", lambda _: cal_btn.config(bg=BORDER, fg=CYAN))

        # La ventana recién creada (frameless + transient) puede abrirse
        # detrás de la principal: traerla al frente ya en el primer clic.
        win.update_idletasks()
        win.deiconify()
        win.lift()
        win.focus_force()
        win.after(10, lambda: (win.lift(), win.focus_force())
                 if win.winfo_exists() else None)

    def _make_slider(self, parent, label, var_name, lbl_name,
                     from_, to, resolution, default, fmt):
        row = tk.Frame(parent, bg=CARD)
        row.pack(fill="x", padx=16, pady=(0, 2))

        tk.Label(row, text=label, font=("Segoe UI", 9),
                 fg=TEXT, bg=CARD).pack(side="left")

        val = getattr(self, var_name, None)
        if val is None:
            val = tk.DoubleVar(value=default)
            setattr(self, var_name, val)

        val_lbl = tk.Label(row, text=fmt(val.get()),
                           font=("Segoe UI", 9, "bold"),
                           fg=CYAN, bg=CARD, width=5)
        val_lbl.pack(side="right")
        setattr(self, lbl_name, val_lbl)

        def on_change(v):
            val_lbl.config(text=fmt(float(v)))
            if var_name == "delay_val":
                self.bot.delay = float(v)
            else:
                self.bot.threshold = float(v)

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

    def _toggle(self):
        if self.bot_active:
            self.bot.stop()
            self.bot_active = False
            self._update_status(False)
        else:
            self.bot_active = True
            self._update_status(True)
            self.bot.delay = self.delay_val.get()
            self.bot.threshold = self.thresh_val.get()
            self.bot.auto_deactivate = self.auto_deactivate_var.get()
            self.bot_thread = threading.Thread(target=self.bot.start, daemon=True)
            self.bot_thread.start()

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

    def _on_partida_aceptada(self, auto_deactivated=True):
        count = self.bot.partidas_aceptadas
        def _update():
            self.count_lbl.config(text=f"Partidas aceptadas: {count}")
            if auto_deactivated:
                self.bot_active = False
                self._update_status(False)
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
        try:
            if self.bot_active:
                self.bot.stop()
        except Exception:
            pass
        self.root.destroy()

    def run(self):
        self.root.mainloop()


# ──────────────────────────────────────────────
if __name__ == "__main__":
    App().run()
