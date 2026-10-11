# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller specification file for Personal AI OS standalone backend.

Builds a standalone onedir Windows distribution containing the FastAPI application,
Uvicorn server, SQLite database drivers, ChromaDB, sentence-transformers,
and all required agent tooling dependencies.
"""

import os
import sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# Collect package data files for libraries with migrations or assets
datas = []
datas += collect_data_files('chromadb')
datas += collect_data_files('sentence_transformers')
datas += collect_data_files('transformers')
datas += collect_data_files('uvicorn')
datas += collect_data_files('fastapi')

# Collect hidden imports for dynamic imports and plugins
hiddenimports = []
hiddenimports += collect_submodules('app')
hiddenimports += collect_submodules('uvicorn')
hiddenimports += collect_submodules('chromadb')
hiddenimports += collect_submodules('sentence_transformers')
hiddenimports += collect_submodules('sqlalchemy.dialects.sqlite')
hiddenimports += [
    'sqlite3',
    'pydantic',
    'pydantic_settings',
    'starlette.middleware.cors',
    'duckduckgo_search',
    'ddgs',
    'icalendar',
    'docx',
    'pptx',
    'pypdf',
    'torch',
    'transformers',
    'huggingface_hub',
    'git',
    'github',
    'anyio._backends._asyncio',
]

# Development / testing tools excluded to keep bundle clean
excludes = [
    'pytest',
    'pytest_asyncio',
    'tkinter',
    'IPython',
    'notebook',
]

a = Analysis(
    ['run_server.py'],
    pathex=['.'],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='personal_ai_backend',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='personal_ai_backend',
)
