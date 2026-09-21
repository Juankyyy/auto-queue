"""
bot.py — Lógica principal del bot de auto-aceptación para LoL
"""

import cv2
import numpy as np
import pyautogui
import random
import threading
import time
import os
import sys
from PIL import ImageGrab, Image

# Failsafe activado a propósito: mover el mouse a la esquina superior
# izquierda aborta el control automático (medida de seguridad).
pyautogui.FAILSAFE = True


def _bundled_path(*parts):
    """Ruta a un recurso empaquetado (funciona en .py y en .exe de PyInstaller)."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, *parts)
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), *parts)


def _user_data_dir():
    """Carpeta escribible (junto al .exe si está congelado)."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def _resolve_template_path():
    """El template se puede recalibrar: prioriza el de junto al .exe, si no el empaquetado."""
    user_copy = os.path.join(_user_data_dir(), "templates", "accept_btn.png")
    if os.path.exists(user_copy):
        return user_copy
    return _bundled_path("templates", "accept_btn.png")


TEMPLATE_PATH = _resolve_template_path()


class LoLAutoAccept:
    def __init__(self, log_callback=None, accepted_callback=None):
        """
        log_callback: función que recibe un str para mostrar en el log
        accepted_callback: función que recibe un bool (auto_deactivated)
        """
        self.log = log_callback or print
        self.on_accepted = accepted_callback or (lambda _: None)
        self._run_event = threading.Event()
        self.partidas_aceptadas = 0
        self.delay = 0.5          # segundos antes de hacer clic
        self.threshold = 0.80     # confianza mínima (0-1)
        self.poll_interval = 0.5  # segundos entre capturas
        self.auto_deactivate = True # si True, se apaga tras aceptar una partida

    @property
    def running(self):
        """Compatibilidad: True mientras el loop debe seguir activo."""
        return self._run_event.is_set()

    @running.setter
    def running(self, value):
        if value:
            self._run_event.set()
        else:
            self._run_event.clear()

    # ------------------------------------------------------------------
    # Control del loop
    # ------------------------------------------------------------------

    def start(self):
        self._run_event.set()
        self.log("🟢 Bot activado. Monitoreando pantalla...")
        self._loop()

    def stop(self):
        if self._run_event.is_set():
            self._run_event.clear()
            self.log("🔴 Bot detenido.")

    def _sleep_interruptible(self, seconds):
        """Espera por tramos para que stop() interrumpa sin demora larga."""
        end = time.monotonic() + max(0.0, seconds)
        while self._run_event.is_set():
            remaining = end - time.monotonic()
            if remaining <= 0:
                break
            time.sleep(min(0.05, remaining))

    # ------------------------------------------------------------------
    # Loop principal
    # ------------------------------------------------------------------

    def _loop(self):
        template = self._load_template()

        while self._run_event.is_set():
            try:
                screenshot = self._capture_screen()

                if template is not None:
                    found, location = self._match_template(screenshot, template)
                else:
                    # Fallback: detección por color del botón cyan/teal
                    found, location = self._detect_by_color(screenshot)

                if found and location:
                    actual_delay = max(0.05, self.delay + random.uniform(-0.1, 0.2))
                    self.log(f"✅ ¡Partida encontrada! Aceptando en {actual_delay:.2f}s...")
                    self._sleep_interruptible(actual_delay)
                    if not self._run_event.is_set():
                        break
                    try:
                        self._click(location)
                    except pyautogui.FailSafeException:
                        self.log("⚠️ Failsafe de pyautogui: mouse en la esquina, bot detenido.")
                        self._run_event.clear()
                        break
                    self.partidas_aceptadas += 1
                    self.log(f"🎮 Partida #{self.partidas_aceptadas} aceptada.")

                    if self.auto_deactivate:
                        self._run_event.clear()
                        self.on_accepted(True)
                        break
                    else:
                        self.on_accepted(False)
                        self.log("⏳ En espera... Manteniendo bot activo por si se cancela la cola.")
                        # Esperar a que la ventana de diálogo desaparezca (interrumpible)
                        self._sleep_interruptible(6)

            except pyautogui.FailSafeException:
                self.log("⚠️ Failsafe de pyautogui: bot detenido.")
                self._run_event.clear()
                break
            except Exception as e:
                self.log(f"⚠️ Error: {e}")

            self._sleep_interruptible(self.poll_interval)

    # ------------------------------------------------------------------
    # Captura de pantalla
    # ------------------------------------------------------------------

    def _capture_screen(self):
        screenshot = ImageGrab.grab()
        return cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)

    # ------------------------------------------------------------------
    # Detección por template matching (OpenCV)
    # ------------------------------------------------------------------

    def _load_template(self):
        # Re-resolver en cada carga: el template puede recalibrarse en caliente.
        global TEMPLATE_PATH
        TEMPLATE_PATH = _resolve_template_path()
        if not os.path.exists(TEMPLATE_PATH):
            self.log("⚠️ Template no encontrado. Usando detección por color como respaldo.")
            return None
        template = cv2.imread(TEMPLATE_PATH, cv2.IMREAD_COLOR)
        if template is None:
            self.log(f"⚠️ Template ilegible ({TEMPLATE_PATH}). Usando detección por color.")
            return None
        self.log("📄 Template del botón ¡ACEPTAR! cargado correctamente.")
        return template

    def _match_template(self, screenshot, template):
        """Busca el template en el screenshot. Retorna (found, center_point)."""
        result = cv2.matchTemplate(screenshot, template, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)

        if max_val >= self.threshold:
            h, w = template.shape[:2]
            center_x = max_loc[0] + w // 2
            center_y = max_loc[1] + h // 2
            return True, (center_x, center_y)
        return False, None

    # ------------------------------------------------------------------
    # Detección por color (fallback sin template)
    # ------------------------------------------------------------------

    def _detect_by_color(self, screenshot):
        """
        Detecta el botón ¡ACEPTAR! buscando el color cyan/teal
        característico del borde del botón en el cliente de LoL.
        """
        hsv = cv2.cvtColor(screenshot, cv2.COLOR_BGR2HSV)

        # Rango de color del borde cyan-azul del botón Aceptar
        lower_cyan = np.array([85, 150, 150])
        upper_cyan = np.array([100, 255, 255])
        mask = cv2.inRange(hsv, lower_cyan, upper_cyan)

        # Encontrar contornos del área cyan
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        for cnt in contours:
            area = cv2.contourArea(cnt)
            # El botón Aceptar tiene un área de contorno considerable
            if 500 < area < 50000:
                x, y, w, h = cv2.boundingRect(cnt)
                # El botón es más ancho que alto (forma de píldora)
                if w > h * 1.5:
                    center_x = x + w // 2
                    center_y = y + h // 2
                    return True, (center_x, center_y)

        return False, None

    # ------------------------------------------------------------------
    # Click
    # ------------------------------------------------------------------

    def _click(self, location):
        """Mueve el mouse y hace clic con un ligero offset aleatorio."""
        x, y = location
        offset_x = self._random_offset(range_px=8)
        offset_y = self._random_offset(range_px=4)
        pyautogui.moveTo(x + offset_x, y + offset_y, duration=0.15)
        pyautogui.click()

    # ------------------------------------------------------------------
    # Calibración — captura el template desde pantalla
    # ------------------------------------------------------------------

    def capture_template(self):
        """
        Toma un screenshot, busca por color el botón Aceptar,
        recorta esa región y la guarda como template.
        Retorna True si tuvo éxito.
        """
        self.log("📸 Capturando template en 3 segundos... Asegúrate de tener el popup visible.")
        time.sleep(3)

        screenshot = self._capture_screen()
        found, location = self._detect_by_color(screenshot)

        if not found or not location:
            self.log("❌ No se detectó el botón. Abre el popup de 'PARTIDA ENCONTRADA' primero.")
            return False

        # Recortar área alrededor del botón
        x, y = location
        margin = 40
        h, w = screenshot.shape[:2]
        x1 = max(0, x - 120)
        y1 = max(0, y - margin)
        x2 = min(w, x + 120)
        y2 = min(h, y + margin)

        cropped = screenshot[y1:y2, x1:x2]

        # Guardar template (junto al .exe si está congelado, para que persista)
        os.makedirs(os.path.join(_user_data_dir(), "templates"), exist_ok=True)
        save_path = os.path.join(_user_data_dir(), "templates", "accept_btn.png")
        cv2.imwrite(save_path, cropped)
        # Actualizar la ruta en caliente para esta sesión
        global TEMPLATE_PATH
        TEMPLATE_PATH = save_path
        self.log(f"✅ Template guardado correctamente en: {save_path}")
        return True

    # ------------------------------------------------------------------
    # Utilidades
    # ------------------------------------------------------------------

    @staticmethod
    def _random_offset(range_px=5):
        return random.randint(-range_px, range_px)
