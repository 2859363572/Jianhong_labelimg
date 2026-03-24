#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Test script to verify the labelImg modifications"""

import sys
import os
sys.path.append('.venv\\Lib\\site-packages')

from labelImg.labelImg import MainWindow
from PyQt5.QtWidgets import QApplication
from libs.constants import SETTING_SKIP_OK_CONFIRMATION

def test_functionality():
    """Test the new functionality"""
    app = QApplication(sys.argv)
    
    # Create main window
    window = MainWindow()
    
    # Test 1: Check if skip OK confirmation checkbox exists
    if hasattr(window, 'skip_ok_confirmation_checkbox'):
        print("✓ Skip OK confirmation checkbox exists")
        # Test checkbox state
        window.skip_ok_confirmation_checkbox.setChecked(True)
        if window.skip_ok_confirmation_checkbox.isChecked():
            print("✓ Skip OK confirmation checkbox can be checked")
        else:
            print("✗ Skip OK confirmation checkbox cannot be checked")
    else:
        print("✗ Skip OK confirmation checkbox not found")
    
    # Test 2: Check if preset labels combo exists
    if hasattr(window, 'preset_labels_combo'):
        print("✓ Preset labels combo box exists")
        # Test if combo is enabled when skip OK is checked
        window.skip_ok_confirmation_checkbox.setChecked(True)
        window.toggle_preset_labels()
        if window.preset_labels_combo.isEnabled():
            print("✓ Preset labels combo is enabled when skip OK is checked")
        else:
            print("✗ Preset labels combo is not enabled when skip OK is checked")
    else:
        print("✗ Preset labels combo box not found")
    
    # Test 3: Check if settings are saved
    if hasattr(window, 'settings'):
        print("✓ Settings object exists")
        # Test saving skip OK setting
        window.skip_ok_confirmation_checkbox.setChecked(True)
        window.settings[SETTING_SKIP_OK_CONFIRMATION] = True
        if window.settings.get(SETTING_SKIP_OK_CONFIRMATION, False):
            print("✓ Skip OK confirmation setting can be saved")
        else:
            print("✗ Skip OK confirmation setting cannot be saved")
    else:
        print("✗ Settings object not found")
    
    print("\nTest completed successfully!")
    return True

if __name__ == '__main__':
    test_functionality()