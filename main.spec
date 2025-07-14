# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files

datas = [('data', 'data')]
datas += collect_data_files('matplotlib')
datas += collect_data_files('PyQt5')


a = Analysis(
    ['main.py'],
    pathex=['C:/temp/venv/Lib/site-packages/PyQt5/Qt5/plugins'],
    binaries=[],
    datas=datas,
    hiddenimports=['numpy,scipy,matplotlib,PyQt5.sip'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='main',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['13.ico'],
)
