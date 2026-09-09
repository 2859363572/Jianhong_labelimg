# -*- mode: python ; coding: utf-8 -*-

import os.path
import sys
from PyInstaller.utils.hooks import collect_submodules

# Determine base directory from the build working directory.
# This spec is intended to be invoked from the repository root.
base_dir = os.getcwd()

# Collect data files
datas = []

# Include img directory
img_dir = os.path.join(base_dir, 'img')
if os.path.exists(img_dir):
    for f in os.listdir(img_dir):
        fp = os.path.join(img_dir, f)
        if os.path.isfile(fp):
            datas.append((fp, 'img'))

# Include data directory
data_dir = os.path.join(base_dir, 'data')
if os.path.exists(data_dir):
    for f in os.listdir(data_dir):
        fp = os.path.join(data_dir, f)
        if os.path.isfile(fp):
            datas.append((fp, 'data'))

# Manually collect PyQt5 since it's not treated as a package by PyInstaller
binaries = []
import PyQt5
pyqt5_dir = os.path.dirname(PyQt5.__file__)

# Collect PyQt5 .pyd files (the actual Qt bindings)
for f in os.listdir(pyqt5_dir):
    fp = os.path.join(pyqt5_dir, f)
    if f.endswith('.pyd'):
        binaries.append((fp, 'PyQt5'))
    # Include .dll files at root level
    elif f.endswith('.dll'):
        binaries.append((fp, '.'))

# Collect Qt5 shared libraries (DLLs)
qt5_dir = os.path.join(pyqt5_dir, 'Qt5')
if os.path.exists(qt5_dir):
    for f in os.listdir(qt5_dir):
        fp = os.path.join(qt5_dir, f)
        if f.endswith('.dll'):
            binaries.append((fp, 'PyQt5/Qt5'))

# Collect Qt plugins (platforms, imageformats, styles)
plugins_dir = os.path.join(qt5_dir, 'plugins')
if os.path.exists(plugins_dir):
    for root, dirs, files in os.walk(plugins_dir):
        for f in files:
            if f.endswith('.dll'):
                fp = os.path.join(root, f)
                rel = os.path.relpath(root, pyqt5_dir)
                binaries.append((fp, rel))

# Collect sip module (bundled with PyQt5)
sip_file = os.path.join(pyqt5_dir, 'sip.cp312-win_amd64.pyd')
if os.path.exists(sip_file):
    binaries.append((sip_file, 'PyQt5'))

# Include PyQt5 uic module data
datas.append((os.path.join(pyqt5_dir, 'uic'), 'PyQt5/uic'))

# Collect all libs submodules automatically
libs_submodules = collect_submodules('libs')

a = Analysis(
    ['run.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=[
        'onnxruntime',
        'xxhash',
    ] + libs_submodules,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib',
        'scipy',
        'notebook',
        'ipython',
        'setuptools.tests',
        'pytest',
    ],
    noarchive=False,
    optimize=1,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='labelImg',
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
    icon=['img\\labelimg.ico'],
)
