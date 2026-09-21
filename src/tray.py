"""
tray.py — Iconos de estado e icono de la bandeja del sistema.

SystemTray encapsula pystray: la App solo le pasa el root de Tk,
un proveedor de estado y las acciones del menú.
"""

import os
import threading
from collections.abc import Callable

import pystray
from PIL import Image, ImageDraw
from pystray import Menu as TrayMenu
from pystray import MenuItem as TrayItem

from paths import bundled_path

APP_NAME = "LoL Auto Queue"
TITLE_ACTIVE = "LoL Auto Queue — ACTIVO"
TITLE_IDLE = "LoL Auto Queue — INACTIVO"
TASKBAR_SIZES = (16, 24, 32, 48)


def load_base_icon() -> "Image.Image":
    """Carga el icono de la app (PNG nuevo primero, respaldo sólido)."""
    for candidate in (
        bundled_path("assets", "icons", "app_icon.png"),
        bundled_path("assets", "templates", "logo.png"),
    ):
        if os.path.exists(candidate):
            try:
                return Image.open(candidate).convert("RGBA")
            except Exception:
                pass
    return Image.new("RGBA", (256, 256), (200, 155, 60, 255))


def badged_size(base: "Image.Image", size: int) -> "Image.Image":
    """Variante 'activo': base reescalada a `size` con punto verde nítido."""
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


def default_tray_image(base: "Image.Image") -> "Image.Image":
    """Icono para la bandeja (64x64)."""
    return base.resize((64, 64), Image.Resampling.LANCZOS)


class SystemTray:
    """Controla el icono de bandeja y los iconos de estado (bandeja + tarea)."""

    def __init__(self, root, is_active: Callable[[], bool],
                 on_show: Callable[[], None],
                 on_toggle: Callable[[], None],
                 on_settings: Callable[[], None],
                 on_quit: Callable[[], None],
                 on_log: Callable[[str], None],
                 on_map: Callable[[], None],
                 on_unmap: Callable[[], None],
                 photo_factory: Callable[["Image.Image"], object]) -> None:
        self._root = root
        self._is_active = is_active
        self._on_show = on_show
        self._on_toggle = on_toggle
        self._on_settings = on_settings
        self._on_quit = on_quit
        self._on_log = on_log
        self._cb_map = on_map
        self._cb_unmap = on_unmap
        self._photo_factory = photo_factory
        self._icon: pystray.Icon | None = None
        self._img_off = None
        self._img_on = None
        self._photos_off: list = []
        self._photos_on: list = []

    # ── Ciclo de vida ──

    def setup(self) -> None:
        """Construye iconos, menú y arranca pystray en hilo daemon."""
        self._build_status_icons()
        menu = TrayMenu(
            TrayItem('Mostrar ventana',
                     lambda icon, _: self._root.after(0, self._on_show),
                     default=True, visible=False),
            TrayItem(
                lambda _: "Desactivar bot" if self._is_active() else "Activar bot",
                lambda icon, _: self._root.after(0, self._on_toggle)),
            TrayItem("Abrir configuraciones",
                     lambda icon, _: self._root.after(0, self._on_settings)),
            TrayItem("Cerrar", lambda icon, _: self._root.after(0, self._on_quit)),
        )
        self._icon = pystray.Icon(APP_NAME, self.tray_image(), TITLE_IDLE, menu)
        threading.Thread(target=self._icon.run, daemon=True).start()
        self._root.bind("<Map>", lambda _: self._on_map())
        self._root.bind("<Unmap>", lambda _: self._on_unmap())

    def stop(self) -> None:
        try:
            if self._icon is not None:
                self._icon.stop()
        except Exception:
            pass

    def refresh_menu(self) -> None:
        try:
            if self._icon is not None:
                self._icon.update_menu()
        except Exception:
            pass

    # ── Iconos de estado ──

    def _build_status_icons(self) -> None:
        """Prepara variantes inactivo/activo a máxima resolución."""
        try:
            base = load_base_icon()  # resolución nativa (523px)
            self._img_off = base.resize((64, 64), Image.Resampling.LANCZOS)
            self._img_on = badged_size(base, 64)
            try:
                # Varios tamaños para que Windows no tenga que reescalar
                self._photos_off = [
                    self._photo_factory(base.resize((s, s), Image.Resampling.LANCZOS))
                    for s in TASKBAR_SIZES]
                self._photos_on = [
                    self._photo_factory(badged_size(base, s))
                    for s in TASKBAR_SIZES]
            except Exception:
                pass
        except Exception:
            pass

    def tray_image(self) -> "Image.Image":
        """Icono para la bandeja (64x64)."""
        if self._img_off is not None:
            return self._img_off
        try:
            return default_tray_image(load_base_icon())
        except Exception:
            return Image.new("RGBA", (64, 64), (200, 155, 60, 255))

    def apply_status(self, active: bool) -> None:
        """Punto verde en bandeja + barra de tareas + tooltip según estado.

        Solo se usa iconphoto (nítido). El iconbitmap del .ico se deja fijo
        desde el arranque: intercambiarlo en caliente pixelaba la barra.
        """
        try:
            if self._icon is not None:
                img = self._img_on if active else self._img_off
                if img is not None:
                    self._icon.icon = img
                self._icon.title = TITLE_ACTIVE if active else TITLE_IDLE
        except Exception:
            pass
        try:
            photos = self._photos_on if active else self._photos_off
            if photos:
                self._root.iconphoto(True, *photos)
        except Exception:
            pass

    # ── Visibilidad ──

    def _on_map(self) -> None:
        try:
            self._cb_map()
        except Exception:
            pass
        self.refresh_menu()

    def _on_unmap(self) -> None:
        try:
            self._cb_unmap()
        except Exception:
            pass
        self.refresh_menu()
