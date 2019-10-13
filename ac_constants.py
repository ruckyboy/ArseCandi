# -*- coding: utf-8 -*-
#----------------------------------------------------------------------------
# Name:         ac_constants.py
# Purpose:
#
# Author:       Peter Todd
#
# Created:      1 January 2019
# Version:      1.0
# Date:         13 October 2019
# Licence:
# Tags:
#----------------------------------------------------------------------------
"""
This module contains the constants used by iCandi.
"""
from pathlib import Path

__author__ = "Peter Todd <peter.todd@uwa.edu.au>"
__date__ = "13 October 2019"

"""
App
"""
APP_NAME = "iCandi - you'll never take me alive..."
BUILD_VER = "1.0.0.19_10_13"

"""
File and Folder
"""
CWD = Path.cwd()
DATA_DIR = CWD / "data"  # directory location for underlying json and preference files
RESOURCE_DIR = CWD / "resources"  # directory location for resources like images, icons, etc
CAM_IMAGE_DIR = RESOURCE_DIR / "cam_images"  # directory of random filler mp4s for camview object

"""
AirTable
"""
ERROR_CODES = {"401": "Unauthorized - Check Bearer Key",
               "404": "Not Found - Check URL",
               "408": "Read timed out - 8 seconds",
               "422": "Invalid Request - The request data is invalid",
               "500": "Internal Server Error - AirTable server problem",
               "503": "Service Unavailable - AirTable server could not process your request in time."}

""" 
Fonts 
"""
APP_FS = 9  # Default application font size

""" 
Colours 
"""
COLOUR_PANEL_BG = "#616161"  # "#4B4B4B"  # "#ECECEC"  "#B0BEC5"   #607D8B #B0BEC5 #339194
COLOUR_TABLE_BG = "#757575"
COLOUR_TABLE_HEADER_BG = "#424242"
COLOUR_ODD_LISTROW = "#8F8F8F"  # "#F2F2F2"  # "#ECECEC" "#F5F5F5"
COLOUR_EVEN_LISTROW = "#A4A4A4"  # "#E4E4E4"  # "#E0E1E3" "#EEEEEE"
COLOUR_TEXT_LARGE = "#757575"  # "#838b8b"
COLOUR_TEXT_LABELS = "#EFEFEF"
COLOUR_TEXT_DATA = "#FFFFFF"
COLOUR_STATUS_BAR = "#363636"
COLOUR_BUTTON_DEFAULT = "#FF8F00"  # "#E65100"   # "#E17227"  # "#EFDFC0"
COLOUR_BUTTON_INACTIVE = "#DCAF93"
COLOUR_BUTTON_DISABLED = "#BB4D00"  # "#9B7963"
COLOUR_BUTTON_ACTIVE = "#DCAF93"
COLOUR_BUTTON_TEXT_LIGHT = "#EFEFEF"
COLOUR_BUTTON_TEXT_DISABLED = "#8E8E8E"
COLOUR_BUTTON_TEXT_DARK = "#000000"
COLOUR_BUTTON_TEXT_ACTIVE = "#0BA1F8"
COLOUR_BUTTON_TEXT_ALERT = "#FF3300"
