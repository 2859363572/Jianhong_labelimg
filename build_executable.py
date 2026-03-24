#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Build script to create executable for labelImg with modifications"""

import PyInstaller.__main__
import os
import sys

def build_executable():
    """Build the executable using PyInstaller"""
    
    # PyInstaller configuration
    args = [
        '.venv\\Lib\\site-packages\\labelImg\\labelImg.py',  # Main script
        '--name=labelImg',  # Name of the executable
        '--windowed',  # No console window
        '--onefile',  # Single executable file
        '--hidden-import=libs',
        '--hidden-import=libs.constants',
        '--hidden-import=libs.utils',
        '--hidden-import=libs.settings',
        '--hidden-import=libs.shape',
        '--hidden-import=libs.canvas',
        '--hidden-import=libs.zoomWidget',
        '--hidden-import=libs.labelDialog',
        '--hidden-import=libs.colorDialog',
        '--hidden-import=libs.labelFile',
        '--hidden-import=libs.toolBar',
        '--hidden-import=libs.pascal_voc_io',
        '--hidden-import=libs.yolo_io',
        '--hidden-import=libs.create_ml_io',
        '--hidden-import=libs.ustr',
        '--hidden-import=libs.hashableQListWidgetItem',
        '--hidden-import=libs.stringBundle',
        '--hidden-import=libs.resources',
        '--hidden-import=PyQt5',
        '--hidden-import=PyQt5.QtCore',
        '--hidden-import=PyQt5.QtGui',
        '--hidden-import=PyQt5.QtWidgets',
        '--hidden-import=lxml',
        '--hidden-import=lxml._elementpath',
        '--hidden-import=PIL',
        '--hidden-import=PIL.Image',
        '--hidden-import=PIL.ImageQt',
        '--hidden-import=xxhash',
        '--collect-all=libs',
        '--clean',  # Clean build
        '--noconfirm',  # Overwrite existing files
    ]
    
    print("Building executable...")
    print("This may take a few minutes...")
    
    try:
        PyInstaller.__main__.run(args)
        print("✓ Build completed successfully!")
        print(f"✓ Executable created at: dist\\labelImg_mod.exe")
        return True
    except Exception as e:
        print(f"✗ Build failed: {e}")
        return False

if __name__ == '__main__':
    success = build_executable()
    sys.exit(0 if success else 1)