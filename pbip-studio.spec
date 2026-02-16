# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for PBIP Studio
Build: pyinstaller pbip-studio.spec
"""

import sys
from pathlib import Path

block_cipher = None

# Collect data files - use Tree for better handling of non-Python files
datas = [
    ('src/database/schema.py', 'database'),
    ('src/models', 'models'),
    ('src/parsers', 'parsers'),
    ('src/services', 'services'),
    ('logos', 'logos'),
    ('pbip-studio.ico', '.'),
    ('USER_GUIDE.html', '.'),
    ('USER_GUIDE.md', '.'),
    ('COMPLETE_DOCUMENTATION.md', '.'),
]

# Hidden imports that PyInstaller might miss
hiddenimports = [
    'PyQt6.QtCore',
    'PyQt6.QtWidgets',
    'PyQt6.QtGui',
    'PyQt6.QtWebEngineWidgets',
    'fastapi',
    'uvicorn',
    'uvicorn.loops',
    'uvicorn.loops.auto',
    'uvicorn.protocols',
    'uvicorn.protocols.http',
    'uvicorn.protocols.http.auto',
    'uvicorn.protocols.websockets',
    'uvicorn.protocols.websockets.auto',
    'uvicorn.lifespan',
    'uvicorn.lifespan.on',
    'pydantic',
    'sqlite3',
    'pandas',
    'plotly',
    'qtawesome',
    'requests',
    'cryptography',
    'cryptography.fernet',
    'cryptography.hazmat',
    'cryptography.hazmat.primitives',
    'cryptography.hazmat.backends',
    'utils.data_source_migration',
    'utils.table_rename',
    'utils.column_rename',
    'utils.pbir_connection_manager',
    'utils.theme_manager',
]

a = Analysis(
    ['src/main.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
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
    name='PBIP-Studio',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # No console window for GUI app
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='pbip-studio.ico',
)
