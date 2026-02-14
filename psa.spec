# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[
        # Core
        'PyQt6',
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.QtWidgets',
        'PyQt6.QtMultimedia',
        
        # Database
        'sqlite3',
        
        # Encryption
        'cryptography',
        'cryptography.fernet',
        
        # Web & Search
        'requests',
        'urllib3',
        'bs4',
        'lxml',
        
        # DuckDuckGo Search (FIXED)
        'duckduckgo_search',
        'duckduckgo_search.duckduckgo_search',
        'ddgs',
        
        # AI APIs
        'cerebras',
        'cerebras.cloud',
        'cerebras.cloud.sdk',
        'google.generativeai',
        
        # Vision
        'PIL',
        'PIL.Image',
        
        # Document Processing
        'PyPDF2',
        'docx',
        
        # Text-to-Speech
        'gtts',
        'pygame',
        'pyttsx3',
        
        # Speech Recognition
        'speech_recognition',
        'pyaudio',
        
        # Markdown
        'markdown',
        'markdown.extensions',
        'markdown.extensions.fenced_code',
        'markdown.extensions.tables',
        
        # Other
        'pathlib',
        'json',
        'base64',
        'datetime',
        'tempfile',
        're',
        'os',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib',
        'numpy',
        'pandas',
    ],
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
    name='PSA',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console = False,# No console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='PSA.ico',
)