# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec para LoL Auto Queue -> un solo .exe con icono y assets."""

import os

block_cipher = None


def _app_version():
    """Versión desde version.txt (la actualiza el workflow Auto Release)."""
    try:
        with open(os.path.join(SPECPATH, 'version.txt'), encoding='utf-8') as f:
            return f.read().strip() or '0.0.0'
    except OSError:
        return '0.0.0'


def _version_tuple(version):
    parts = []
    for chunk in version.split('.'):
        digits = ''.join(c for c in chunk if c.isdigit())
        parts.append(int(digits) if digits else 0)
    while len(parts) < 4:
        parts.append(0)
    return tuple(parts[:4])


APP_VERSION = _app_version()
APP_VER_TUPLE = _version_tuple(APP_VERSION)

# Recurso de versión de Windows (visible en Propiedades > Detalles del .exe).
# Se genera aquí para que cada build lleve el número de la release.
_version_info_path = os.path.join(SPECPATH, 'file_version_info.txt')
with open(_version_info_path, 'w', encoding='utf-8') as f:
    f.write(f"""VSVersionInfo(
  ffi=FixedFileInfo(
    filevers={APP_VER_TUPLE},
    prodvers={APP_VER_TUPLE},
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo(
      [
        StringTable(
          '040904B0',
          [StringStruct('CompanyName', 'LoL Auto Queue'),
           StringStruct('FileDescription', 'LoL Auto Queue'),
           StringStruct('FileVersion', '{APP_VERSION}'),
           StringStruct('InternalName', 'LoLAutoQueue'),
           StringStruct('OriginalFilename', 'LoLAutoQueue.exe'),
           StringStruct('ProductName', 'LoL Auto Queue'),
           StringStruct('ProductVersion', '{APP_VERSION}')])
      ]
    ),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
""")

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('templates', 'templates'),
        ('app_icon.png', '.'),
        ('app_icon.ico', '.'),
        ('version.txt', '.'),
    ],
    hiddenimports=[
        'PIL._tkinter_finder',
        'pystray._win32',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='LoLAutoQueue',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # sin consola: app con GUI (tkinter frameless + tray)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='app_icon.ico',
    version=_version_info_path,
)
