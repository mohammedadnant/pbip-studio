"""
Setup script for building Windows installer (MSI)
Build: python setup.py bdist_msi

PBIP Studio - Free and Open Source
"""

from cx_Freeze import setup, Executable
import sys
from pathlib import Path

# Include files - copy to lib for proper module import
include_files = [
    ('src/gui', 'lib/gui'),  # Include GUI package
    ('src/api', 'lib/api'),  # Include API package
    ('src/database', 'lib/database'),
    ('src/models', 'lib/models'),
    ('src/parsers', 'lib/parsers'),
    ('src/services', 'lib/services'),
    ('src/utils', 'lib/utils'),
    ('data', 'data'),  # Include database folder
    ('logos', 'logos'),  # Include logo files
    ('pbip-studio.ico', 'pbip-studio.ico'),  # Include icon
    ('config.md', 'config.md'),  # Blank config file - users fill via UI
    ('README.md', 'README.md'),  # Project readme
    ('LICENSE', 'LICENSE'),  # MIT License
]

# Dependencies
build_exe_options = {
    'packages': [
        'PyQt6',
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.QtWidgets',
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
        'pydantic_core',
        'sqlite3',
        'pandas',
        'plotly',
        'qtawesome',
        'requests',
        'openpyxl',
        'dotenv',
        'asyncio',
        'multiprocessing',
        'threading',
        'starlette',
        'starlette.routing',
        'starlette.middleware',
        # Azure Authentication
        'azure',
        'azure.identity',
        'azure.core',
        'azure.core.credentials',
        'azure.core.exceptions',
        'msal',
        'msal.application',
        'msal.authority',
        # Cryptography for license manager
    'include_files': include_files,
    'excludes': ['tkinter', 'unittest', 'test'],
    'optimize': 2,
    'build_exe': 'build/exe.win-amd64-3.12',
}

# MSI options
bdist_msi_options = {
    'add_to_path': False,
    'initial_target_dir': r'[ProgramFilesFolder]\PBIP Studio',
    'install_icon': 'pbip-studio.ico',
    'upgrade_code': '{12345678-1234-1234-1234-123456789ABC}',  # For updates
    'all_users': True,  # Install for all users
}

# Base for GUI application (no console)
base = None
if sys.platform == 'win32':
    base = 'Win32GUI'

setup(
    name='PBIP Studio',
    version='1.0.0',
    description='Professional Power BI Project Studio for Fabric migration and management',
    author='PBIP Tools',
    long_description='Complete studio environment with pre-configured database, documentation, and config templates',
    options={
        'build_exe': build_exe_options,
        'bdist_msi': bdist_msi_options,
    },
    executables=[
        Executable(
            'src/Free and open-source Power BI development toolkit',
    author='PBIP Studio Contributors',
    long_description='A comprehensive toolkit for working with Power BI PBIP/TMDL files',
    license='MIT
            icon='pbip-studio.ico',
            shortcut_name='PBIP Studio',
            shortcut_dir='ProgramMenuFolder',  # Start Menu
        )
    ]
)
