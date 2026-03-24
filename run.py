#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Launcher for labelImg with modifications"""

import sys
import os

# Add the site-packages directory to sys.path
# This ensures that 'labelImg' and 'libs' can be imported correctly
site_packages_path = os.path.join(os.path.dirname(__file__), '.venv', 'Lib', 'site-packages')
if os.path.exists(site_packages_path):
    sys.path.insert(0, site_packages_path)
else:
    print(f"Error: Site-packages directory not found at {site_packages_path}")
    sys.exit(1)

from labelImg.labelImg import main

if __name__ == '__main__':
    # Run the application
    sys.exit(main())
