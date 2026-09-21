<p align="center">🌐 <a href="README.md"><strong>Read in English</strong></a></p>

<p align="center">
  <img src="templates/logo.png" alt="LoL Auto Queue" width="160" />
</p>

<h1 align="center">LoL Auto Queue</h1>

<p align="center">
  Acepta partidas de League of Legends automáticamente.
</p>

<p align="center">
  <a href="https://github.com/Juankyyy/auto-queue/releases/latest"><img src="https://img.shields.io/github/v/release/Juankyyy/auto-queue?logo=github&logoColor=white" alt="Última release" /></a>
  <img src="https://img.shields.io/badge/Python-3.12-blue?logo=python&logoColor=white" alt="Python 3.12" />
  <img src="https://img.shields.io/badge/Windows-10%20%2F%2011-0078D4?logo=windows&logoColor=white" alt="Windows" />
  <img src="https://img.shields.io/badge/UI-Tkinter-green" alt="Tkinter" />
  <img src="https://img.shields.io/badge/Visi%C3%B3n-OpenCV-red?logo=opencv" alt="OpenCV" />
</p>

---

## ¿Qué es?

**LoL Auto Queue** es una aplicación de escritorio para Windows que vigila tu pantalla y **acepta sola la partida** cuando aparece el popup de *"Partida encontrada"* del cliente de League of Legends. Ideal para esos momentos en los que estás en cola y te alejas del PC unos minutos.

Detecta el botón **¡ACEPTAR!** por reconocimiento de imagen (OpenCV Template Matching, con respaldo por detección de color) y hace clic por ti con un pequeño retardo aleatorio para un comportamiento más natural.

> 🚻 **Uso responsable:** está creada para ausencias cortas como ir al baño o a la cocina por algo de comer. No se recomienda para ausentarte mucho tiempo ni fomentamos abandonar las colas: si lo activas debes estar listo para jugar.

## Características

- ✅ **Auto-aceptación** del popup de partida encontrada.
- 🎯 **Doble detección**: Template Matching (OpenCV) + respaldo por color cyan.
- ⏱️ **Delay configurable** (0.1 – 3.0 s) con variación aleatoria anti-detección.
- 🎚️ **Umbral de detección ajustable** (50 – 99 %).
- 🔒 **Auto-desactivación** tras aceptar, o modo continuo por si alguien cancela la cola.
- 📸 **Calibración**: captura tu propio template si cambias de resolución.
- 🖥️ **Ventana frameless** personalizada (sin bordes de Windows), arrastrable.
- 🔔 **Bandeja del sistema**: icono con punto verde de estado, menú (activar/desactivar, configuraciones, cerrar) y clic para mostrar la ventana.
- 📊 **Estadísticas** por día, semana, mes y año: partidas, activaciones, tiempo activo y promedios.
- 💾 **Persistencia**: ajustes y estadísticas se guardan entre sesiones (`config.json`, `stats.json`).
- 📝 **Registro colapsable** de eventos en la ventana principal.
- 🛡️ **Instancia única**: no se abre dos veces; reabrirla muestra la ventana existente.

## Instalación

Requisitos: **Windows 10/11** con **Python 3.12**.

```bat
pip install -r requirements.txt
```

O simplemente ejecuta:

```bat
Iniciar Bot.bat
```

## Uso

1. Abre la app y pulsa **ACTIVAR BOT**.
2. Entra en cola en League of Legends.
3. Cuando aparezca la partida, el bot la acepta solo. 🎮
4. (Opcional) Abre **⚙ Ajustes** para calibrar el template con **📸 Capturar Nuevo Template** teniendo el popup visible (te da 3 segundos).

> ⚠️ Úsalo bajo tu responsabilidad. La automatización de clientes de juego puede ir en contra de los términos de servicio de Riot Games.

## Configuración

Los ajustes se guardan automáticamente en `config.json`:

| Clave             | Descripción                              | Defecto |
|-------------------|------------------------------------------|---------|
| `delay`           | Segundos antes de hacer clic             | `0.5`   |
| `threshold`       | Confianza mínima de detección (0–1)      | `0.8`   |
| `auto_deactivate` | Apagarse tras aceptar una partida        | `true`  |
| `close_to_tray`   | La ✕ minimiza a bandeja en vez de salir  | `true`  |
| `log_visible`     | Mostrar el registro al arrancar          | `true`  |

## Estructura del proyecto

```
auto-queue/
├── main.py              # Interfaz gráfica (Tkinter) + bandeja + stats
├── bot.py               # Detección (OpenCV) y clic automático
├── requirements.txt     # Dependencias
├── Iniciar Bot.bat      # Lanzador en Windows
├── app_icon.ico/.png    # Iconos de la app
├── config.json          # Ajustes (se genera solo)
├── stats.json           # Estadísticas (se genera solo)
└── templates/
    ├── logo.png         # Logo de la app
    └── accept_btn.png   # Template del botón ¡ACEPTAR!
```

## Tecnologías

- **Tkinter** — interfaz gráfica frameless
- **OpenCV + NumPy** — Template Matching y detección por color
- **PyAutoGUI + Pillow** — captura de pantalla y clic
- **pystray** — icono de bandeja del sistema

---

<p align="center">
  <img src="app_icon.png" alt="icono" width="48" />
  <br />
  Hecho para no perder ni una cola. 🎮
</p>
