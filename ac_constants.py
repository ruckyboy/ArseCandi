# -*- coding: utf-8 -*-
#----------------------------------------------------------------------------
# Name:         ac_constants.py
# Purpose:
#
# Author:       Peter Todd
#
# Created:      1 January 2019
# Version:
# Date:         17 March 2019
# Licence:
# Tags:
#----------------------------------------------------------------------------
"""
This module contains all the constants used by ArseCandi.
"""
from pathlib import Path

__author__ = "Peter Todd <peter.todd@uwa.edu.au>"
__date__ = "09 April 2019"

"""
App
"""
APP_NAME = "ArseCandi"
BUILD_VER = "0.9.09_04_17"

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
"""
#ACE4FA bright blue
#72BCD7 lightblue       #D86E27 Orange      # Orange Yellow
#60A9C5 mid blue        #A59D88 Tan         #483E37 Brown
#41718B darker blue     #80796A Dark Tan    #2D2724 Dark Brown
#31566B Darkest Blue
#CD6F4E red brown       #151514 Brown black 
"""
"""
From SourceForge
#FFFFFF White - background
#F2F2F2 very light grey - stripping
#E4E4E4 light grey - stripping
#747474 light mid grey - stripping
#5F5F5F mid grey - title bar
#4B4B4B mid dark grey - background block
#363636 dark grey - header background block
#71C7FC light blue - text highlight
#0BA1F8 mid-light blue - text on white
#E17227 bright orange - navigation bar
#FF3300 darker orange - button background with white text - inverts on rollover, white with blue text
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

""" 
PyInstaller info
pyinstaller.exe cli.py --name ArseCandi --onefile -w --uac-admin
H:\Drive\PythonProjects\iCandi2018\venv\Scripts\pyinstaller.exe ac_GUI.py --name ArseCandi --onefile -w
H:\Drive\PythonProjects\iCandi2018\venv\Scripts\pyinstaller.exe ac_GUI_gui.py --name ArseCandi --onefile -w --uac-admin
Package up with Advanced Installer 15.9

--name ArseCandi    change name to ArseCandi; 
--onefile       in one executable file; 
--uac-admin     user access control: runs as admin
-w              do not show console window on .exe launch

"""