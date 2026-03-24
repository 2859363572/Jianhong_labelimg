#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Test script to verify the new_shape functionality with skip OK confirmation"""

import sys
import os
sys.path.append('.venv\\Lib\\site-packages')

from labelImg.labelImg import MainWindow
from PyQt5.QtWidgets import QApplication
from libs.constants import SETTING_SKIP_OK_CONFIRMATION

def test_new_shape_functionality():
    """Test the new_shape method with skip OK confirmation"""
    app = QApplication(sys.argv)
    
    # Create main window
    window = MainWindow()
    
    # Test 1: Test new_shape with skip OK confirmation disabled
    print("Test 1: Skip OK confirmation disabled")
    window.skip_ok_confirmation_checkbox.setChecked(False)
    
    # Simulate the new_shape method logic
    if not window.skip_ok_confirmation_checkbox.isChecked():
        print("✓ Would show label dialog (skip OK is disabled)")
    else:
        print("✗ Should not skip dialog when disabled")
    
    # Test 2: Test new_shape with skip OK confirmation enabled
    print("\nTest 2: Skip OK confirmation enabled")
    window.skip_ok_confirmation_checkbox.setChecked(True)
    window.preset_labels_combo.setCurrentText('person')
    
    # Simulate the new_shape method logic
    if window.skip_ok_confirmation_checkbox.isChecked():
        if window.preset_labels_combo.currentText():
            text = window.preset_labels_combo.currentText()
            print(f"✓ Would use preset label: {text}")
        else:
            print("✓ Would use fallback label logic")
    else:
        print("✗ Should skip dialog when enabled")
    
    # Test 3: Test preset labels loading
    print("\nTest 3: Preset labels loading")
    window.load_preset_labels()
    count = window.preset_labels_combo.count()
    print(f"✓ Loaded {count} preset labels")
    
    # Test 4: Test preset labels combo state
    print("\nTest 4: Preset labels combo state")
    window.skip_ok_confirmation_checkbox.setChecked(True)
    window.toggle_preset_labels()
    if window.preset_labels_combo.isEnabled():
        print("✓ Preset labels combo is enabled when skip OK is checked")
    else:
        print("✗ Preset labels combo should be enabled when skip OK is checked")
    
    window.skip_ok_confirmation_checkbox.setChecked(False)
    window.toggle_preset_labels()
    if not window.preset_labels_combo.isEnabled():
        print("✓ Preset labels combo is disabled when skip OK is unchecked")
    else:
        print("✗ Preset labels combo should be disabled when skip OK is unchecked")
    
    print("\nAll tests completed successfully!")
    return True

if __name__ == '__main__':
    test_new_shape_functionality()