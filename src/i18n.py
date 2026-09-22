"""
i18n.py — Textos de la interfaz en inglés (por defecto) y español.

El idioma se fija al arrancar con set_language() y se lee con t().
Cambiar de idioma en ajustes guarda y reinicia la app.
"""

LANGS = ("en", "es")
DEFAULT_LANG = "en"

_current = DEFAULT_LANG

_MONTHS = {
    "en": ("January", "February", "March", "April", "May", "June",
           "July", "August", "September", "October", "November", "December"),
    "es": ("enero", "febrero", "marzo", "abril", "mayo", "junio",
           "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"),
}

_STRINGS = {
    "en": {
        # Botón principal y estado
        "start_bot": "START BOT",
        "stop_bot": "STOP BOT",
        "status_active": "ACTIVE",
        "status_idle": "IDLE",
        "log_title": "LOG",
        "boot_msg": "System started. Press START to begin.",
        # Páginas
        "page_settings": "Settings",
        "page_stats": "Statistics",
        "settings_title": "SETTINGS",
        "stats_title": "STATISTICS",
        # Ajustes: detección
        "det_times": "DETECTION & TIMING",
        "delay_label": "Accept delay",
        "threshold_label": "Detection threshold",
        # Ajustes: al aceptar
        "on_accept": "ON MATCH ACCEPT",
        "disable_bot": "🔒 Disable",
        "keep_active": "🔄 Keep active",
        "beh_disable_desc": "The bot turns off after accepting. "
                            "You'll need to enable it again for the next queue.",
        "beh_keep_desc": "The bot keeps watching in case someone cancels "
                         "or declines the current match.",
        # Ajustes: template
        "tpl_title": "RECOGNITION TEMPLATE",
        "tpl_desc": "If you change screen resolution, you can capture "
                   "the button again.",
        "capture_btn": "  📸  Capture New Template  ",
        # Ajustes: al cerrar
        "on_close": "ON APP CLOSE",
        "quit_btn": "⏻ Quit",
        "tray_btn": "📥 Tray",
        "close_tray_desc": "The ✕ hides the window and the app keeps running "
                           "in the Windows tray icons.",
        "close_quit_desc": "The ✕ stops the bot and closes the app completely.",
        # Ajustes: idioma
        "lang_title": "LANGUAGE",
        "lang_desc": "The app will restart to apply the language.",
        # Estadísticas
        "period_title": "PERIOD",
        "period_day": "Day",
        "period_week": "Week",
        "period_month": "Month",
        "period_year": "Year",
        "st_matches": "🎮  Matches accepted",
        "st_activations": "▶  Times enabled",
        "st_time": "⏱  Active time",
        "st_avg_act": "📈  Average per activation",
        "st_avg_sess": "⏳  Average session",
        "st_live": "🟢  Current session",
        "reset_stats": "↺  Reset statistics",
        "reset_confirm": "Click again to confirm?",
        "stats_reset_done": "📊 Statistics reset.",
        # Calibración y aceptadas
        "calib_busy": "⚠️ Stop the bot before calibrating.",
        "calib_started": "📸 Calibration started — 3 seconds to show the popup...",
        "accepted_auto": "🔒 Bot auto-disabled after accepting.",
        "accepted_keep": "🔄 Bot stays active in case the queue is cancelled.",
        "tray_failed": "⚠️ Could not create the tray icon: {err}",
        # Bandeja
        "tray_show": "Show window",
        "tray_enable": "Enable bot",
        "tray_disable": "Disable bot",
        "tray_settings": "Open settings",
        "tray_quit": "Quit",
        "tray_active": "LoL Auto Queue — ACTIVE",
        "tray_idle": "LoL Auto Queue — IDLE",
        # Bot (log)
        "bot_started": "🟢 Bot enabled. Monitoring screen...",
        "bot_stopped": "🔴 Bot stopped.",
        "match_found": "✅ Match found! Accepting in {secs}s...",
        "match_accepted": "🎮 Match #{n} accepted.",
        "waiting_keep": "⏳ Waiting... Keeping the bot active in case "
                        "the queue is cancelled.",
        "failsafe_corner": "⚠️ PyAutoGUI failsafe: mouse in the corner, bot stopped.",
        "failsafe_stopped": "⚠️ PyAutoGUI failsafe: bot stopped.",
        "error_prefix": "⚠️ Error: {err}",
        "template_missing": "⚠️ Template not found. Using color detection as fallback.",
        "template_unreadable": "⚠️ Unreadable template ({path}). Using color detection.",
        "template_loaded": "📄 ACCEPT! button template loaded successfully.",
        "capturing_template": "📸 Capturing template in 3 seconds... "
                              "Make sure the popup is visible.",
        "no_button": "❌ Button not detected. Open the 'MATCH FOUND' popup first.",
        "template_saved": "✅ Template saved successfully to: {path}",
    },
    "es": {
        # Botón principal y estado
        "start_bot": "ACTIVAR BOT",
        "stop_bot": "DETENER BOT",
        "status_active": "ACTIVO",
        "status_idle": "INACTIVO",
        "log_title": "REGISTRO",
        "boot_msg": "Sistema iniciado. Presiona ACTIVAR para comenzar.",
        # Páginas
        "page_settings": "Ajustes",
        "page_stats": "Estadísticas",
        "settings_title": "AJUSTES",
        "stats_title": "ESTADÍSTICAS",
        # Ajustes: detección
        "det_times": "DETECCIÓN Y TIEMPOS",
        "delay_label": "Delay al aceptar",
        "threshold_label": "Umbral de detección",
        # Ajustes: al aceptar
        "on_accept": "AL ACEPTAR PARTIDA",
        "disable_bot": "🔒 Desactivar",
        "keep_active": "🔄 Mantener activo",
        "beh_disable_desc": "El bot se apaga al aceptar. Deberás volver a activarlo "
                            "para la siguiente cola.",
        "beh_keep_desc": "El bot sigue buscando por si alguien cancela "
                         "o rechaza la partida actual.",
        # Ajustes: template
        "tpl_title": "TEMPLATE DE RECONOCIMIENTO",
        "tpl_desc": "Si cambias de resolución de pantalla, puedes volver "
                   "a capturar el botón.",
        "capture_btn": "  📸  Capturar Nuevo Template  ",
        # Ajustes: al cerrar
        "on_close": "AL CERRAR LA APP",
        "quit_btn": "⏻ Salir",
        "tray_btn": "📥 Bandeja",
        "close_tray_desc": "La ✕ oculta la ventana y la app sigue en los iconos "
                           "de Windows.",
        "close_quit_desc": "La ✕ detiene el bot y cierra la app por completo.",
        # Ajustes: idioma
        "lang_title": "IDIOMA",
        "lang_desc": "La app se reiniciará para aplicar el idioma.",
        # Estadísticas
        "period_title": "PERIODO",
        "period_day": "Día",
        "period_week": "Semana",
        "period_month": "Mes",
        "period_year": "Año",
        "st_matches": "🎮  Partidas aceptadas",
        "st_activations": "▶  Veces activado",
        "st_time": "⏱  Tiempo activo",
        "st_avg_act": "📈  Promedio por activación",
        "st_avg_sess": "⏳  Sesión promedio",
        "st_live": "🟢  Sesión actual",
        "reset_stats": "↺  Restablecer estadísticas",
        "reset_confirm": "¿Tocar de nuevo para confirmar?",
        "stats_reset_done": "📊 Estadísticas restablecidas.",
        # Calibración y aceptadas
        "calib_busy": "⚠️ Detén el bot antes de calibrar.",
        "calib_started": "📸 Calibración iniciada — 3 segundos para mostrar el popup...",
        "accepted_auto": "🔒 Bot desactivado automáticamente tras aceptar.",
        "accepted_keep": "🔄 Bot continúa activo por si se cancela la cola.",
        "tray_failed": "⚠️ No se pudo crear el icono de bandeja: {err}",
        # Bandeja
        "tray_show": "Mostrar ventana",
        "tray_enable": "Activar bot",
        "tray_disable": "Desactivar bot",
        "tray_settings": "Abrir configuraciones",
        "tray_quit": "Cerrar",
        "tray_active": "LoL Auto Queue — ACTIVO",
        "tray_idle": "LoL Auto Queue — INACTIVO",
        # Bot (log)
        "bot_started": "🟢 Bot activado. Monitoreando pantalla...",
        "bot_stopped": "🔴 Bot detenido.",
        "match_found": "✅ ¡Partida encontrada! Aceptando en {secs}s...",
        "match_accepted": "🎮 Partida #{n} aceptada.",
        "waiting_keep": "⏳ En espera... Manteniendo bot activo por si se cancela la cola.",
        "failsafe_corner": "⚠️ Failsafe de pyautogui: mouse en la esquina, bot detenido.",
        "failsafe_stopped": "⚠️ Failsafe de pyautogui: bot detenido.",
        "error_prefix": "⚠️ Error: {err}",
        "template_missing": "⚠️ Template no encontrado. Usando detección por color como respaldo.",
        "template_unreadable": "⚠️ Template ilegible ({path}). Usando detección por color.",
        "template_loaded": "📄 Template del botón ¡ACEPTAR! cargado correctamente.",
        "capturing_template": "📸 Capturando template en 3 segundos... "
                              "Asegúrate de tener el popup visible.",
        "no_button": "❌ No se detectó el botón. Abre el popup de 'PARTIDA ENCONTRADA' primero.",
        "template_saved": "✅ Template guardado correctamente en: {path}",
    },
}


def set_language(code):
    """Fija el idioma actual ('en' o 'es'); cualquier otro cae a inglés."""
    global _current
    _current = code if code in LANGS else DEFAULT_LANG
    return _current


def get_language():
    """Código del idioma actual."""
    return _current


def t(key, **kwargs):
    """Texto en el idioma actual, con formato opcional tipo str.format."""
    template = _STRINGS.get(_current, {}).get(key)
    if template is None:
        template = _STRINGS["en"].get(key, key)
    try:
        return template.format(**kwargs)
    except Exception:
        return template


def months():
    """Nombres de los 12 meses en el idioma actual."""
    return _MONTHS.get(_current, _MONTHS["en"])
