#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Test script to verify the updated preset labels"""

import sys
import os
sys.path.append('.venv\\Lib\\site-packages')

from labelImg.labelImg import MainWindow
from PyQt5.QtWidgets import QApplication

def test_updated_preset_labels():
    """Test the updated preset labels functionality"""
    app = QApplication(sys.argv)
    
    # Create main window
    window = MainWindow()
    
    # Test 1: Enable skip OK confirmation to activate preset labels
    window.skip_ok_confirmation_checkbox.setChecked(True)
    window.toggle_preset_labels()
    
    # Test 2: Check if new preset labels are loaded
    expected_labels = ['pedestrian', 'vehicle', 'nonmotro', 'traffic_cone', 'warning_triangle', 'cyclist', 'motorcyclis', 'ttricyclist']
    
    print("Testing updated preset labels:")
    print(f"Expected labels: {expected_labels}")
    
    # Get actual labels from combo box
    actual_labels = []
    for i in range(window.preset_labels_combo.count()):
        actual_labels.append(window.preset_labels_combo.itemText(i))
    
    print(f"Actual labels: {actual_labels}")
    
    # Test 3: Verify all expected labels are present
    all_found = True
    for label in expected_labels:
        if label in actual_labels:
            print(f"✓ Found label: {label}")
        else:
            print(f"✗ Missing label: {label}")
            all_found = False
    
    # Test 4: Test preset label selection
    if window.preset_labels_combo.count() > 0:
        window.preset_labels_combo.setCurrentText('pedestrian')
        selected_text = window.preset_labels_combo.currentText()
        print(f"✓ Selected preset label: {selected_text}")
    else:
        print("✗ No preset labels available")
        all_found = False
    
    if all_found:
        print("\n✓ All tests passed! Updated preset labels are working correctly.")
    else:
        print("\n✗ Some tests failed.")
    
    return all_found

if __name__ == '__main__':
    test_updated_preset_labels()