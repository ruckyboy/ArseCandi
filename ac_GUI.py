import time
import subprocess

import wx
import wx.html
import wx.html2
import wx.grid
from wx.lib.delayedresult import startWorker
import wx.lib.inspection  # only used for inspecting wx widgets
from wx.adv import Sound
from wx.adv import AboutDialogInfo
from wx.lib.dialogs import MultiMessageBox as MultiMessageBox

from ObjectListView import ObjectListView, ColumnDefn, Filter

from ac_constants import *
import arsecandi
import ac_utility
import ac_ping
import ac_html

"""  
Naming Abbreviations:

btn:    Button
rbtn:   RadioButton
tbtn:   ToggleButton
comb:   ComboBox (Choice)
ckb:    CheckBox
lab:    Label
olv:    ObjectListView
txt:    TextControl
webv:   WebViewer

_run - internal application
_launch - external application
"""

prefs_dict = ac_utility.preferences(DATA_DIR)


###########################################################################
# Class VenuesPanel
###########################################################################

class VenuesPanel(wx.Panel):
    pause_device_updating = False  # used to halt populating venue details while the cursor buttons are held down
    venue_textsearch_filter = None
    venue_ctf_filter = None
    venue_ctrl_filter = None
    venue_filter_args = []  # Holds the constructed arguments for applying filter/s to the venue_olv
    device_show_flagged = prefs_dict["devicelist_show_flagged"]
    autoping_active = prefs_dict["ping_on_select"]

    def __init__(self, parent):
        wx.Panel.__init__(self, parent, id=wx.ID_ANY, pos=wx.DefaultPosition, size=wx.Size(-1, -1),
                          style=wx.TAB_TRAVERSAL, name="venues_panel_master")
        self.SetForegroundColour(wx.Colour(COLOUR_BUTTON_TEXT_LIGHT))
        self.SetBackgroundColour(wx.Colour(COLOUR_PANEL_BG))
        self.SetMinSize(wx.Size(1412, 840))

        fnt = self.GetFont()
        fnt.SetPointSize(APP_FS + 1)
        self.SetFont(fnt)

        self.timer = wx.Timer(self)
        self.cam_html = None

        self.last_device = None  # keeping track of tooltip messages to prevent flicker

        """
        ### Initiate empty framework for GUI elements
        """

        panel_sizer = wx.BoxSizer(wx.HORIZONTAL)

        """ ### Venues Section """
        venues_section_static_box = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY, "Select a venue"), wx.VERTICAL)
        vss_gsb = venues_section_static_box.GetStaticBox()  # A helper variable to use with StaticBoxSizer members
        apply_text_template(vss_gsb)

        venues_section_sizer = wx.BoxSizer(wx.VERTICAL)

        """ Venues Search TextBox """
        self.venues_search_tb = wx.SearchCtrl(self, wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.Size(-1, -1),
                                              wx.TE_PROCESS_ENTER)
        self.venues_search_tb.ShowSearchButton(False)
        self.venues_search_tb.ShowCancelButton(True)
        self.venues_search_tb.SetForegroundColour(COLOUR_TEXT_LARGE)
        self.venues_search_tb.SetFont(
            wx.Font(12, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL, False, "Segoe UI Semibold"))
        venues_section_sizer.Add(self.venues_search_tb, 0, wx.LEFT | wx.RIGHT | wx.TOP | wx.EXPAND, 5)

        """ Venues List Filter 'selections' """

        venues_filter_sizer = wx.BoxSizer(wx.HORIZONTAL)

        self.ctf_filter_ckb = wx.CheckBox(self, wx.ID_ANY, " CTF Filter: Off ", wx.DefaultPosition, wx.Size(180, -1),
                                          wx.CHK_3STATE | wx.CHK_ALLOW_3RD_STATE_FOR_USER)
        self.ctf_filter_ckb.SetToolTip("Checked: CTF Only\nUnchecked: Non-CTF Only\nNeither: No Filtering")
        self.ctf_filter_ckb.Set3StateValue(wx.CHK_UNDETERMINED)
        self.ctf_filter_ckb.SetFont(
            wx.Font(10, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL, False, "Segoe UI Semibold"))
        venues_filter_sizer.Add(self.ctf_filter_ckb, 0, wx.ALL, 6)

        self.controlled_filter_ckb = wx.CheckBox(self, wx.ID_ANY, " Controlled Filter: Off ", wx.DefaultPosition,
                                                 wx.DefaultSize, wx.CHK_3STATE | wx.CHK_ALLOW_3RD_STATE_FOR_USER)
        self.controlled_filter_ckb.SetToolTip(
            "Checked: Controlled Only\nUnchecked: Non-controlled Only\nNeither: No Filtering")
        self.controlled_filter_ckb.Set3StateValue(wx.CHK_UNDETERMINED)
        self.controlled_filter_ckb.SetFont(
            wx.Font(10, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL, False, "Segoe UI Semibold"))
        venues_filter_sizer.Add(self.controlled_filter_ckb, 0, wx.ALL, 6)

        venues_section_sizer.Add(venues_filter_sizer, 0, wx.EXPAND, 5)

        """ Venues Object List View """
        self.venue_olv = ObjectListView(self, wx.ID_ANY, wx.DefaultPosition, wx.Size(-1, -1),
                                        style=wx.LC_REPORT | wx.LC_SINGLE_SEL | wx.NO_BORDER)
        self.venue_olv.SetColumns([
            ColumnDefn("Venue", "left", 290, "name", minimumWidth=290),
            ColumnDefn("AKA", "left", 0, "aka", maximumWidth=0),
            ColumnDefn("Room", "left", 80, "code", minimumWidth=80),
            ColumnDefn("Booking", "left", 0, "bookingid", maximumWidth=0),
            ColumnDefn("Area", "left", 150, "group", minimumWidth=80, isSpaceFilling=True)])
        #  BookingID and AKA fields hidden so that they can be included in the search lookup
        self.venue_olv.SetMinSize(wx.Size(500, -1))
        self.venue_olv.SetBackgroundColour(COLOUR_EVEN_LISTROW)
        self.venue_olv.evenRowsBackColor = wx.Colour(COLOUR_EVEN_LISTROW)
        self.venue_olv.oddRowsBackColor = wx.Colour(COLOUR_ODD_LISTROW)
        self.venue_olv.SetEmptyListMsg("No matching venues")
        self.venue_olv.SetEmptyListMsgColors(wx.WHITE, wx.Colour(COLOUR_EVEN_LISTROW))

        venues_section_sizer.Add(self.venue_olv, 1, wx.ALL | wx.EXPAND, 5)

        """ Venues List Count Label """
        self.venues_count_label = wx.StaticText(self, wx.ID_ANY, "", wx.DefaultPosition, wx.DefaultSize, wx.ALIGN_RIGHT)
        self.venues_count_label.SetFont(
            wx.Font(10, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL, False, "Segoe UI Semibold"))
        self.venues_count_label.SetForegroundColour(COLOUR_BUTTON_TEXT_LIGHT)

        venues_section_sizer.Add(self.venues_count_label, 0, wx.ALL | wx.EXPAND, 5)
        venues_section_static_box.Add(venues_section_sizer, 2, wx.EXPAND, 5)
        panel_sizer.Add(venues_section_static_box, 2, wx.ALL | wx.EXPAND, 10)

        """ ### Venue Devices and Details Section """
        venue_all_info_sizer = wx.BoxSizer(wx.HORIZONTAL)

        """ ### Venue Devices Section """
        device_section_static_box = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY, "Device controls"), wx.VERTICAL)
        dvss_gsb = device_section_static_box.GetStaticBox()  # A helper variable to use with StaticBoxSizer members
        apply_text_template(dvss_gsb)
        device_section_sizer = wx.BoxSizer(wx.VERTICAL)

        """ Device Object List View """
        device_box_sizer = wx.BoxSizer(wx.HORIZONTAL)
        device_list_sizer = wx.BoxSizer(wx.VERTICAL)

        self.device_olv = ObjectListView(self, wx.ID_ANY | wx.EXPAND, wx.DefaultPosition, wx.Size(-1, -1),
                                         sortable=False, style=wx.LC_REPORT | wx.LC_SINGLE_SEL | wx.NO_BORDER)
        self.device_olv.SetColumns([
            ColumnDefn("Address", "left", -1, 1, fixedWidth=105, isSearchable=False),
            ColumnDefn("Device", "left", -1, 0, minimumWidth=150, isSpaceFilling=True, isSearchable=False),
            ColumnDefn("Ping", "right", -1, "ping", fixedWidth=100, isSearchable=False)])
        # Ping is a generated result
        self.device_olv.SetBackgroundColour(COLOUR_EVEN_LISTROW)
        self.device_olv.evenRowsBackColor = wx.Colour(COLOUR_EVEN_LISTROW)
        self.device_olv.oddRowsBackColor = wx.Colour(COLOUR_ODD_LISTROW)
        self.device_olv.SetEmptyListMsg("No devices")
        self.device_olv.SetEmptyListMsgColors(wx.WHITE, wx.Colour(COLOUR_EVEN_LISTROW))
        self.device_olv.SetSizeHints((365, 325), (555, -1))

        self.device_olv.SetMinSize(wx.Size(365, 325))

        device_list_sizer.Add(self.device_olv, 2, wx.ALL | wx.EXPAND, 0)

        """ Device List Filtering """
        devicelist_filter_sizer = wx.BoxSizer(wx.HORIZONTAL)

        self.flagged_ckb = wx.CheckBox(self, wx.ID_ANY, " Include Flagged", wx.DefaultPosition, wx.Size(100, -1), 0)
        self.flagged_ckb.SetFont(
            wx.Font(10, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL, False, "Segoe UI"))
        self.flagged_ckb.SetToolTip(
            "Include all of the ip addresses allocated to a venue\n* Indicates that the address is probably inactive")
        self.flagged_ckb.SetForegroundColour(COLOUR_BUTTON_TEXT_LIGHT)
        devicelist_filter_sizer.Add(self.flagged_ckb, 2, wx.ALL | wx.EXPAND, 5)

        self.device_count_label = wx.StaticText(self, wx.ID_ANY, "Devices:", wx.DefaultPosition, wx.DefaultSize, 0)
        self.device_count_label.SetFont(
            wx.Font(10, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL, False, "Segoe UI Semibold"))
        self.device_count_label.SetForegroundColour(COLOUR_BUTTON_TEXT_LIGHT)
        devicelist_filter_sizer.Add(self.device_count_label, 0, wx.ALL | wx.EXPAND, 5)

        device_list_sizer.Add(devicelist_filter_sizer, 0, wx.EXPAND, 5)

        device_box_sizer.Add(device_list_sizer, 1, wx.ALL | wx.EXPAND, 5)

        self.device_button_line = wx.StaticLine(self, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.LI_VERTICAL)
        device_box_sizer.Add(self.device_button_line, 0, wx.BOTTOM | wx.TOP | wx.EXPAND, 5)

        device_list_buttons_sizer = wx.BoxSizer(wx.VERTICAL)

        self.autoping_btn = wx.ToggleButton(self, wx.ID_ANY, "Auto-Ping", wx.DefaultPosition, wx.DefaultSize,
                                            wx.NO_BORDER)
        self.autoping_btn.SetToolTip("Automatically ping listed venue devices\n(* Will effect the speed of navigation)")
        apply_button_template(self.autoping_btn, "active_toggle" if self.autoping_active else "default")

        device_list_buttons_sizer.Add(self.autoping_btn, 0,
                                      wx.RIGHT | wx.BOTTOM | wx.EXPAND | wx.RESERVE_SPACE_EVEN_IF_HIDDEN, 5)

        self.venue_ping_btn = wx.Button(self, wx.ID_ANY, "Venue Ping", wx.DefaultPosition, wx.DefaultSize, wx.NO_BORDER)
        apply_button_template(self.venue_ping_btn)
        device_list_buttons_sizer.Add(self.venue_ping_btn, 0,
                                      wx.RIGHT | wx.BOTTOM | wx.TOP | wx.EXPAND | wx.RESERVE_SPACE_EVEN_IF_HIDDEN, 5)

        self.ping_btn = wx.Button(self, wx.ID_ANY, "Device Ping", wx.DefaultPosition, wx.DefaultSize, wx.NO_BORDER)
        apply_button_template(self.ping_btn)
        device_list_buttons_sizer.Add(self.ping_btn, 0,
                                      wx.RIGHT | wx.BOTTOM | wx.EXPAND | wx.RESERVE_SPACE_EVEN_IF_HIDDEN, 5)

        device_list_buttons_sizer.Add(wx.Size(0, 10))

        self.webcontrol_btn = wx.Button(self, wx.ID_ANY, "Web Control", wx.DefaultPosition, wx.DefaultSize,
                                        wx.NO_BORDER)
        self.webcontrol_btn.SetToolTip("Right click opens in alternative browser")

        apply_button_template(self.webcontrol_btn)
        device_list_buttons_sizer.Add(self.webcontrol_btn, 0,
                                      wx.RIGHT | wx.BOTTOM | wx.EXPAND | wx.RESERVE_SPACE_EVEN_IF_HIDDEN, 5)

        self.vnc_btn = wx.Button(self, wx.ID_ANY, "VNC", wx.DefaultPosition, wx.DefaultSize, wx.NO_BORDER)
        apply_button_template(self.vnc_btn)
        self.vnc_btn.Enable(False)
        device_list_buttons_sizer.Add(self.vnc_btn, 0,
                                      wx.RIGHT | wx.BOTTOM | wx.EXPAND | wx.RESERVE_SPACE_EVEN_IF_HIDDEN, 5)

        self.telnet_btn = wx.Button(self, wx.ID_ANY, "Telnet", wx.DefaultPosition, wx.DefaultSize, wx.NO_BORDER)
        apply_button_template(self.telnet_btn)
        self.telnet_btn.Enable(False)
        device_list_buttons_sizer.Add(self.telnet_btn, 0,
                                      wx.RIGHT | wx.BOTTOM | wx.EXPAND | wx.RESERVE_SPACE_EVEN_IF_HIDDEN, 5)

        self.reboot_btn = wx.Button(self, wx.ID_ANY, "Reboot", wx.DefaultPosition, wx.DefaultSize, wx.NO_BORDER)
        apply_button_template(self.reboot_btn)
        device_list_buttons_sizer.Add(self.reboot_btn, 0,
                                      wx.RIGHT | wx.BOTTOM | wx.EXPAND | wx.RESERVE_SPACE_EVEN_IF_HIDDEN, 5)

        device_list_buttons_sizer.Add(wx.Size(0, 16))

        self.touchpanel_btn = wx.Button(self, wx.ID_ANY, "Touch Panel", wx.DefaultPosition, wx.DefaultSize,
                                        wx.NO_BORDER)
        self.touchpanel_btn.SetToolTip("Opens first touch panel in device list")
        apply_button_template(self.touchpanel_btn)
        device_list_buttons_sizer.Add(self.touchpanel_btn, 0,
                                      wx.RIGHT | wx.BOTTOM | wx.EXPAND | wx.RESERVE_SPACE_EVEN_IF_HIDDEN, 5)

        self.pc_btn = wx.Button(self, wx.ID_ANY, "DameWare", wx.DefaultPosition, wx.DefaultSize, wx.NO_BORDER)
        self.pc_btn.SetToolTip("Opens first PC in device list")
        apply_button_template(self.pc_btn)
        device_list_buttons_sizer.Add(self.pc_btn, 0,
                                      wx.RIGHT | wx.BOTTOM | wx.EXPAND | wx.RESERVE_SPACE_EVEN_IF_HIDDEN, 5)

        self.echo_btn = wx.Button(self, wx.ID_ANY, "Echo 360", wx.DefaultPosition, wx.DefaultSize, wx.NO_BORDER)
        self.echo_btn.SetToolTip("Opens device's web interface")
        apply_button_template(self.echo_btn)
        device_list_buttons_sizer.Add(self.echo_btn, 0,
                                      wx.RIGHT | wx.BOTTOM | wx.EXPAND | wx.RESERVE_SPACE_EVEN_IF_HIDDEN, 5)

        device_box_sizer.Add(device_list_buttons_sizer, 0, wx.ALL | wx.EXPAND, 5)
        device_section_sizer.Add(device_box_sizer, 5, wx.ALL | wx.EXPAND, 5)

        """ Device List spacer """
        device_section_sizer.Add(wx.Size(500, 0))

        """ WebCam Viewer """
        webcam_sizer = wx.BoxSizer(wx.HORIZONTAL)

        """ Cam viewer window spacer left """
        webcam_sizer.Add((1, 0), 1, wx.EXPAND)  # For horizontally aligning webcam viewer within webcam_sizer

        self.cam_viewer = wx.html2.WebView.New(self, wx.ID_ANY, size=wx.Size(355, 230))
        self.cam_viewer.SetMinSize((355, 230))
        self.cam_viewer.SetMaxSize((355, 230))
        self.cam_viewer.EnableHistory(False)
        self.cam_viewer.Enable(False)
        webcam_sizer.Add(self.cam_viewer, 0, wx.ALL | wx.CENTER, 5)

        """ Cam viewer window spacer right """
        webcam_sizer.Add((1, 0), 1, wx.EXPAND)  # For horizontally aligning webcam viewer within webcam_sizer

        """ WebCam buttons """
        self.webcam_button_line = wx.StaticLine(self, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.LI_VERTICAL)
        webcam_sizer.Add(self.webcam_button_line, 0, wx.BOTTOM | wx.TOP | wx.EXPAND, 5)

        webcam_buttons_sizer = wx.BoxSizer(wx.VERTICAL)

        self.webcam_refresh_btn = wx.ToggleButton(self, wx.ID_ANY, "Monitor", wx.DefaultPosition, wx.DefaultSize,
                                                  wx.NO_BORDER)
        apply_button_template(self.webcam_refresh_btn)

        self.webcam_refresh_btn.SetMinSize(wx.Size(110, -1))
        webcam_buttons_sizer.Add(self.webcam_refresh_btn, 0,
                                 wx.LEFT | wx.TOP | wx.EXPAND | wx.RESERVE_SPACE_EVEN_IF_HIDDEN, 5)

        self.webcam_open_btn = wx.Button(self, wx.ID_ANY, "Camera Type", wx.DefaultPosition, wx.DefaultSize,
                                         wx.NO_BORDER)
        self.webcam_open_btn.SetToolTip("Open camera with browser\n(Right click opens in viewer)")
        apply_button_template(self.webcam_open_btn)
        self.webcam_open_btn.SetMinSize(wx.Size(110, -1))
        webcam_buttons_sizer.Add(self.webcam_open_btn, 0,
                                 wx.LEFT | wx.TOP | wx.EXPAND | wx.RESERVE_SPACE_EVEN_IF_HIDDEN, 5)

        webcam_sizer.Add(webcam_buttons_sizer, 1, wx.ALIGN_RIGHT, 5)

        """ Cam viewer section spacer """
        webcam_sizer.Add((5, 0), 0, wx.EXPAND, 5)  # For horizontally aligning webcam sizer with devicebox sizer
        device_section_sizer.Add(webcam_sizer, 1, wx.ALIGN_RIGHT | wx.ALL, 5)

        device_section_static_box.Add(device_section_sizer, 1, wx.EXPAND, 5)
        venue_all_info_sizer.Add(device_section_static_box, 1, wx.ALL | wx.EXPAND, 10)

        """ ### Venue Details Section """
        details_section_sizer = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY, "Details"), wx.VERTICAL)
        dss_gsb = details_section_sizer.GetStaticBox()  # A helper to use as parent with StaticBoxSizer members
        apply_text_template(dss_gsb)

        """ Venue Details Buttons """
        details_button_sizer = wx.BoxSizer(wx.HORIZONTAL)

        self.airtable_btn = wx.Button(dss_gsb, wx.ID_ANY, "AirTable", wx.DefaultPosition, wx.DefaultSize, wx.NO_BORDER)
        self.airtable_btn.SetToolTip("Right click to open in new window")
        apply_button_template(self.airtable_btn)

        self.asana_btn = wx.Button(dss_gsb, wx.ID_ANY, "Asana", wx.DefaultPosition, wx.DefaultSize, wx.NO_BORDER)
        self.asana_btn.SetToolTip("Right click to open in new window")
        apply_button_template(self.asana_btn)
        self.asana_btn.Hide()

        self.websis_btn = wx.Button(dss_gsb, wx.ID_ANY, "WebSiS", wx.DefaultPosition, wx.DefaultSize, wx.NO_BORDER)
        self.websis_btn.SetToolTip("Right click to open in new window")
        apply_button_template(self.websis_btn)

        self.timetable_btn = wx.Button(dss_gsb, wx.ID_ANY, "Timetable", wx.DefaultPosition, wx.DefaultSize,
                                       wx.NO_BORDER)
        apply_button_template(self.timetable_btn)

        ds_button_params = 0, wx.ALL | wx.EXPAND, 5
        details_button_sizer.AddMany([(self.airtable_btn, *ds_button_params), (self.asana_btn, *ds_button_params),
                                      (self.websis_btn, *ds_button_params), (self.timetable_btn, *ds_button_params)])

        details_section_sizer.Add(details_button_sizer, 0, wx.ALIGN_CENTER_HORIZONTAL | wx.TOP | wx.EXPAND, 5)

        """ Venue Name """
        self.venue_name_text = wx.TextCtrl(dss_gsb, wx.ID_ANY, "Venue Name?", wx.DefaultPosition, wx.Size(240, 50),
                                           wx.TE_READONLY | wx.NO_BORDER | wx.TE_MULTILINE | wx.TE_NO_VSCROLL)
        apply_text_template(self.venue_name_text, "details_venue_name")
        details_section_sizer.Add(self.venue_name_text, 0, wx.ALIGN_CENTER_HORIZONTAL | wx.ALL | wx.EXPAND, 5)

        """ Venue Other Details """
        details_fields_sizer = wx.FlexGridSizer(7, 2, 0, 0)

        self.building_name_label = wx.StaticText(dss_gsb, wx.ID_ANY, "Building", wx.DefaultPosition, wx.Size(-1, -1),
                                                 wx.TE_RIGHT | wx.NO_BORDER)
        self.building_name_text = wx.TextCtrl(dss_gsb, wx.ID_ANY, "?", wx.DefaultPosition, wx.Size(-1, -1),
                                              wx.TE_READONLY | wx.NO_BORDER)

        self.room_number_label = wx.StaticText(dss_gsb, wx.ID_ANY, "Room No.", wx.DefaultPosition, wx.Size(-1, -1),
                                               wx.TE_RIGHT | wx.NO_BORDER)
        self.room_number_text = wx.TextCtrl(dss_gsb, wx.ID_ANY, "?", wx.DefaultPosition, wx.DefaultSize,
                                            wx.TE_READONLY | wx.NO_BORDER)

        self.capacity_label = wx.StaticText(dss_gsb, wx.ID_ANY, "Capacity", wx.DefaultPosition, wx.Size(-1, -1),
                                            wx.TE_RIGHT | wx.NO_BORDER)
        self.capacity_text = wx.TextCtrl(dss_gsb, wx.ID_ANY, "?", wx.DefaultPosition, wx.DefaultSize,
                                         wx.TE_READONLY | wx.NO_BORDER)

        self.ctf_label = wx.StaticText(dss_gsb, wx.ID_ANY, "CTF", wx.DefaultPosition, wx.Size(-1, -1),
                                       wx.TE_RIGHT | wx.NO_BORDER)
        self.ctf_text = wx.TextCtrl(dss_gsb, wx.ID_ANY, "?", wx.DefaultPosition, wx.DefaultSize,
                                    wx.TE_READONLY | wx.NO_BORDER)

        self.phone_label = wx.StaticText(dss_gsb, wx.ID_ANY, "Phone", wx.DefaultPosition, wx.Size(-1, -1),
                                         wx.TE_RIGHT | wx.NO_BORDER)
        self.phone_text = wx.TextCtrl(dss_gsb, wx.ID_ANY, "?", wx.DefaultPosition, wx.DefaultSize,
                                      wx.TE_READONLY | wx.NO_BORDER)

        self.sdc_label = wx.StaticText(dss_gsb, wx.ID_ANY, "SDC Area", wx.DefaultPosition, wx.Size(-1, -1),
                                       wx.TE_RIGHT | wx.NO_BORDER)
        self.sdc_text = wx.TextCtrl(dss_gsb, wx.ID_ANY, "?", wx.DefaultPosition, wx.Size(-1, -1),
                                    wx.TE_READONLY | wx.NO_BORDER)

        details_text_list = [self.building_name_text,
                             self.room_number_text,
                             self.capacity_text,
                             self.ctf_text,
                             self.phone_text,
                             self.sdc_text]

        details_labels_list = [self.building_name_label,
                               self.room_number_label,
                               self.capacity_label,
                               self.ctf_label,
                               self.phone_label,
                               self.sdc_label]

        for label in details_labels_list:
            apply_text_template(label, "details_label")

        for text in details_text_list:
            apply_text_template(text, "details_text")

        ds_label_params = 0, wx.ALIGN_RIGHT | wx.ALL, 5
        ds_text_params = 1, wx.ALIGN_LEFT | wx.ALL | wx.EXPAND, 6

        details_fields_sizer.AddMany([
            (self.building_name_label, *ds_label_params), (self.building_name_text, *ds_text_params),
            (self.room_number_label, *ds_label_params), (self.room_number_text, *ds_text_params),
            (self.capacity_label, *ds_label_params), (self.capacity_text, *ds_text_params),
            (self.ctf_label, *ds_label_params), (self.ctf_text, *ds_text_params),
            (self.phone_label, *ds_label_params), (self.phone_text, *ds_text_params),
            (self.sdc_label, *ds_label_params), (self.sdc_text, *ds_text_params),
        ])

        details_fields_sizer.AddGrowableCol(1, 1)  # Allows text controls column to expand (horizontally)

        details_section_sizer.Add(details_fields_sizer, 0, wx.EXPAND, 5)

        """ Venue Notes """
        self.notes_text = wx.TextCtrl(dss_gsb, wx.ID_ANY, "Notes", wx.Point(-1, -1), wx.Size(236, -1), wx.TE_MULTILINE)
        details_section_sizer.Add(self.notes_text, 1, wx.ALIGN_CENTER_HORIZONTAL | wx.ALL | wx.EXPAND, 5)

        """ Details section spacer """
        details_section_sizer.Add((-1, 10), 0, wx.EXPAND, 5)

        """ Image Viewer (buildings) """
        image_viewer_default = \
            "https://static.weboffice.uwa.edu.au/visualid/core-rebrand/img/uwacrest/uwacrest-white.png"
        self.image_viewer = wx.html2.WebView.New(dss_gsb, wx.ID_ANY, image_viewer_default, wx.DefaultPosition,
                                                 wx.Size(286, 187))
        self.image_viewer.SetMinSize((286, 187))
        self.image_viewer.SetMaxSize((286, 187))
        self.image_viewer.Enable(False)

        details_section_sizer.Add(self.image_viewer, 0, wx.ALIGN_CENTER_HORIZONTAL | wx.ALL, 5)

        venue_all_info_sizer.Add(details_section_sizer, 0, wx.ALL | wx.EXPAND, 10)
        panel_sizer.Add(venue_all_info_sizer, 1, wx.ALL | wx.EXPAND, 0)

        self.SetSizer(panel_sizer)
        self.Layout()

        """
        ### Generate and fill content for GUI elements
        """

        """ Venues List Control - content """
        self.populate_venues_olv()
        self.venue_olv.Focus(0)
        self.olv_venue_selected_evt(-1)  # returns first column's value (record ID)

        """ Device List Control """
        self.flagged_ckb.SetValue(prefs_dict["devicelist_show_flagged"])

        """
        ### Setup event binding connections
        """
        self.venues_search_tb.Bind(wx.EVT_TEXT, self.txt_venues_filter_by_search_evt)
        self.venues_search_tb.Bind(wx.EVT_TEXT_ENTER, self.filter_venues_olv)
        self.venues_search_tb.Bind(wx.EVT_SEARCHCTRL_CANCEL_BTN, self.txt_venues_search_clear_evt)
        self.venue_olv.Bind(wx.EVT_LIST_ITEM_SELECTED, self.olv_venue_selected_evt)
        self.venue_olv.Bind(wx.EVT_KEY_DOWN, self.olv_venue_keydown_evt)
        self.venue_olv.Bind(wx.EVT_KEY_UP, self.olv_venue_keyup_evt)
        self.venue_olv.Bind(wx.EVT_LIST_ITEM_DESELECTED, self.olv_venue_select_none_evt)
        self.ctf_filter_ckb.Bind(wx.EVT_CHECKBOX, self.ckb_venues_filter_by_ctf_evt)
        self.controlled_filter_ckb.Bind(wx.EVT_CHECKBOX, self.ckb_venues_filter_by_control_evt)
        self.device_olv.Bind(wx.EVT_LIST_ITEM_SELECTED, self.olv_device_selected_evt)
        self.device_olv.Bind(wx.EVT_MOTION, self.olv_device_update_tooltip)
        self.flagged_ckb.Bind(wx.EVT_CHECKBOX, self.ckb_device_filter_toggle_evt)
        self.autoping_btn.Bind(wx.EVT_TOGGLEBUTTON, self.btn_autoping_toggle_evt)
        self.venue_ping_btn.Bind(wx.EVT_BUTTON, self.btn_venue_ping_evt)
        self.ping_btn.Bind(wx.EVT_BUTTON, self.btn_ping_evt)
        self.webcontrol_btn.Bind(wx.EVT_BUTTON, self.btn_webcontrol_evt)
        self.webcontrol_btn.Bind(wx.EVT_RIGHT_UP, self.btn_webcontrol_evt)
        self.vnc_btn.Bind(wx.EVT_BUTTON, self.btn_vnc_evt)
        self.telnet_btn.Bind(wx.EVT_BUTTON, self.btn_telnet_evt)
        self.reboot_btn.Bind(wx.EVT_BUTTON, self.btn_reboot_evt)
        self.touchpanel_btn.Bind(wx.EVT_BUTTON, self.btn_touchpanel_evt)
        self.pc_btn.Bind(wx.EVT_BUTTON, self.btn_dameware_evt)
        self.echo_btn.Bind(wx.EVT_BUTTON, self.btn_echo_evt)
        self.cam_viewer.Bind(wx.html2.EVT_WEBVIEW_ERROR, self.webv_webcam_err_evt)
        self.webcam_refresh_btn.Bind(wx.EVT_TOGGLEBUTTON, self.btn_webcam_refresh_evt)
        self.webcam_open_btn.Bind(wx.EVT_BUTTON, self.btn_webcam_open_evt)
        self.webcam_open_btn.Bind(wx.EVT_RIGHT_UP, self.btn_webcam_open_evt)
        self.airtable_btn.Bind(wx.EVT_BUTTON, self.btn_airtable_evt)
        self.airtable_btn.Bind(wx.EVT_RIGHT_UP, self.btn_airtable_evt)
        self.asana_btn.Bind(wx.EVT_BUTTON, self.btn_asana_evt)
        self.asana_btn.Bind(wx.EVT_RIGHT_UP, self.btn_asana_evt)
        self.websis_btn.Bind(wx.EVT_BUTTON, self.btn_websis_evt)
        self.websis_btn.Bind(wx.EVT_RIGHT_UP, self.btn_websis_evt)
        self.timetable_btn.Bind(wx.EVT_BUTTON, self.btn_timetable_evt)
        self.image_viewer.Bind(wx.EVT_LEFT_DCLICK, self.btn_websis_evt)
        self.Bind(wx.EVT_TIMER, self.tmr_webcam_update, self.timer)

        self.device_olv.Select(0)  # only needed to trigger device button formatting when app first started

    """
    ### Venues Panel Class -  event handlers 
    """

    def btn_webcontrol_evt(self, event):
        # opens a web browser to the control page, for laser projectors, Extron controls, etc
        right_click = event.GetEventType() == 10035  # determine if the event type code is wx.EVT_RIGHT_UP
        ipstring = self.device_olv.GetSelectedObject()[1]

        if "Extron Touch Panel" in (self.device_olv.GetSelectedObject()[0]):
            extension = self.device_olv.GetSelectedObject()[2]
            ipstring = f'https://{ipstring}/web/vtlp/{extension}/index.html#/main'

        if not right_click:
            progstring = prefs_dict["main_browser"]
            _launch_main_browser(progstring, ipstring)
        else:
            progstring = prefs_dict["alt_browser"]
            _launch_alt_browser(progstring, ipstring)

    def btn_vnc_evt(self, _):
        # opens a VNC session for AMX touchpanels
        progstring = prefs_dict["vnc"]
        ipstring = self.device_olv.GetSelectedObject()[1]
        self._launch_vnc(progstring, ipstring)

    def _launch_vnc(self, progstring, ipstring):
        try:
            subprocess.Popen([progstring, "-connect host", ipstring])
            # opens vnc with new window at address passed
        except OSError as e:
            print("VNC failed to run:", e)
            msg_warn(self, f"VNC failed to run:\n{progstring}\n{ipstring}\n\nCheck: View -> Settings\n\n{e}")

    def btn_telnet_evt(self, _):
        # opens a telnet shell session
        progstring = prefs_dict["telnet"]
        # TODO reinstate below for uwa use
        ipstring = self.device_olv.GetSelectedObject()[1]
        # ipstring = "35.160.169.47"  # Testing only
        try:
            # For Telnet use Popen with argument shell=True
            subprocess.Popen(["start", "cmd.exe ", progstring, ipstring], shell=True)
            # opens telnet with new window at address passed
        except OSError as e:
            print("Telnet failed to run:", e)
            msg_warn(self, f"Telnet failed to run:\n{progstring}\n\nCheck: View -> Settings\n\n{e}")

    def btn_reboot_evt(self, _):
        # uses the telnet library in ac_utility.py, rather than the old vbs script
        device_type = self.device_olv.GetSelectedObject()[0]
        venue_name = self.venue_olv.GetSelectedObject()['name']
        message = f"You are about to reboot the {device_type} \nin {venue_name}" \
            f"\n\nAre you sure that you want to continue?\n\n"
        # MessageBox and MultiMessageBox - automatically call .ShowModal() when instantiated and .Destroy() when closed
        dlg = wx.MessageBox(message, "Rebooting - is it a good idea?", wx.YES_NO | wx.ICON_WARNING)
        user = None
        pwd = None
        if device_type == "DGX":
            user = "administrator"
            pwd = "password"
        if dlg == wx.YES:
            # TODO reinstate below for uwa use
            ipstring = self.device_olv.GetSelectedObject()[1]
            response = ac_utility.reboot_via_telnet(ipstring, user, pwd)

            MultiMessageBox(f'{venue_name} : {device_type}  [{ipstring}]', "Telnet Session Details...", response)

        pass

    def btn_touchpanel_evt(self, _):
        # opens a vnc or web session for the first listed venue touch-panel (depending on AMX or Extron type)

        for row in range(self.device_olv.GetItemCount()):
            if "Extron Touch Panel" in (self.device_olv.GetItemText(row, 1)):
                progstring = prefs_dict["main_browser"]
                ipstring = self.device_olv.GetItemText(row, 0)
                extension = self.device_olv.GetItemText(row, 3)  # The extension column is not visually present in olv
                full_ipstring = f'https://{ipstring}/web/vtlp/{extension}/vtlp.html'
                _launch_main_browser(progstring, full_ipstring)
                break
            elif "Touch Panel" in (self.device_olv.GetItemText(row, 1)):
                progstring = prefs_dict["vnc"]
                ipstring = self.device_olv.GetItemText(row, 0)
                self._launch_vnc(progstring, ipstring)
                break

    def btn_dameware_evt(self, _):
        # opens a DameWare session for first listed Lectern PC
        # TODO change code or AirTable to handle multiple pc's in venue
        computer_name_string = None
        for row in range(self.device_olv.GetItemCount()):
            if "[Lectern PC]" in (self.device_olv.GetItemText(row, 1)):
                computer_name_string = self.device_olv.GetItemText(row, 0)
                break

        progstring = prefs_dict["dameware"]
        shellstring = "runas.exe /savecred /user:uniwa\\" + prefs_dict["staff_id"]
        try:
            # "runas.exe /savecred /user:uniwa\" + Preferences.UserAccountID + " """ + progstring + " -c: -m:" + ipstring + """"
            subprocess.Popen([shellstring, progstring, " -c: -m:", computer_name_string])
            # opens and logs into Dameware with new window with computerID passed - should ask for password only once
        except OSError as e:
            print("Dameware failed to run:", e)
            msg_warn(self, f"Dameware failed to run:\n{progstring}\n{computer_name_string}\n"
            f"Check: View -> Settings\n\n{e}")

    def btn_echo_evt(self, _):
        # opens a web? session for the first listed venue Echo 360 device
        progstring = prefs_dict["main_browser"]
        for row in range(self.device_olv.GetItemCount()):
            if "[Echo 360]" in (self.device_olv.GetItemText(row, 1)):
                ipstring = self.device_olv.GetItemText(row, 0)
                full_ipstring = f'https://admin:password@{ipstring}/advanced'
                _launch_main_browser(progstring, full_ipstring)
                break

    def webv_webcam_err_evt(self, event):
        print("Webcam Gagged: " + event.GetURL())
        current_venue = self.venue_olv.GetSelectedObject()
        wx.CallAfter(self.populate_camview, current_venue, failed=True)  # Note the format of function name + arguments
        #  waiting until this event finishes before sending request to update page - it's a timing thing

    def btn_webcam_refresh_evt(self, _):
        # wx.CallLater(1000, self.tt_viewer.Reload, flags=1)  # One shot refresh after 1 second
        frequency = prefs_dict["camera_refresh"]  # 1000 = One second refresh rate
        if self.timer.IsRunning():
            self.timer.Stop()
            self.webcam_refresh_btn.SetLabel("Monitor")
            apply_button_template(self.webcam_refresh_btn)
        else:
            self.timer.Start(frequency)
            self.webcam_refresh_btn.SetLabel("Monitoring")
            apply_button_template(self.webcam_refresh_btn, "active_toggle")

    def tmr_webcam_update(self, _):
        if self.cam_html:
            self.cam_viewer.SetPage(self.cam_html, "")
        # Hopefully the above stops the flashing on redraw that occurs when using .Reload()
        # self.cam_viewer.Reload(flags=1)  # Supposedly reloads without cache, seems to work!
        # However .Reload brings the browser window to the front, placing other frames to the back - not handy :(

    def btn_webcam_open_evt(self, event):
        right_click = event.GetEventType() == 10035  # determine if the event type code is wx.EVT_RIGHT_UP
        venue = (self.venue_olv.GetSelectedObject())
        camera_type = venue["webcamtype"]
        camera_ip = venue["webcam"]
        win_size = (640, 480)
        """
        Camera controls
        VB41: Chrome; Suffix=/viewer/live/en/live.html Size=1100x743
        VB50: Firefox; Suffix=/sample/lvahuge.html; Size=833x780
        VB60: Chrome; Suffix=/viewer/live/en/live.html; Size=810x745
        SonyCam: Firefox; Suffix=/en/JViewer.html; Size=860x590
        """
        # TODO Placeholders until live
        # camera_type = "VB60"
        # camera_ip = "136.142.166.244"

        if camera_type == "SonyCam":
            viewer_url = f"http://{camera_ip}/en/JViewer.html"
            win_size = (860, 590)
            ext_browser = "Firefox"
        elif camera_type == "VB41":
            viewer_url = f"http://{camera_ip}/viewer/live/en/live.html"
            win_size = (1100, 743)
            ext_browser = "Chrome"
        elif camera_type == "VB60":
            viewer_url = f"http://{camera_ip}/viewer/live/en/live.html"
            win_size = (870, 820)
            ext_browser = "Chrome"
        elif camera_type == "VB50":
            viewer_url = f"http://{camera_ip}/sample/lvahuge.html"
            win_size = (833, 780)
            ext_browser = "Firefox"
        else:
            viewer_url = f"http://{camera_ip}"
            win_size = (1024, 768)
            ext_browser = "Chrome"

        if right_click:
            WebCamFrame(title=f"{camera_type} - {camera_ip}", size=win_size, address=viewer_url,
                        parent=self.GetParent())
            # webcam_window.Show()
        else:

            if ext_browser == "Chrome":
                progstring = prefs_dict["main_browser"]
                browser_switch = "--new-window"
            else:
                progstring = prefs_dict["alt_browser"]
                browser_switch = "-new-window"
            try:
                subprocess.Popen(
                    [progstring, browser_switch, viewer_url])  # opens browser with new window at address passed
            except OSError as e:
                print("Browser failed to run:", e)
                msg_warn(self, f"Browser failed to run:\n{progstring}\n\nCheck: View -> Settings\n\n{e}")
            event.Skip()

    def btn_airtable_evt(self, event):
        # opens a web browser to the venue's AirTable page
        right_click = event.GetEventType() == 10035  # determine if the event type code is wx.EVT_RIGHT_UP
        venue_record = self.venue_olv.GetSelectedObject()["id"]

        progstring = prefs_dict["main_browser"]
        airtable_prefix_string = prefs_dict["airtable_web"]
        ipstring = f'{airtable_prefix_string}/{venue_record}'
        _launch_main_browser(progstring, ipstring, right_click)

    def btn_asana_evt(self, event):
        # opens a web browser to the venue's Asana tasks
        right_click = event.GetEventType() == 10035
        venue_record = self.venue_olv.GetSelectedObject()["asana"]

        if venue_record == "":
            msg_warn(self, "Venue has no associated Asana tag", self.venue_olv.GetSelectedObject()["name"])
            return

        progstring = prefs_dict["main_browser"]
        asana_prefix_string = "https://app.asana.com/0/"
        ipstring = f'{asana_prefix_string}{venue_record}'
        _launch_main_browser(progstring, ipstring, right_click)

    def btn_websis_evt(self, event):
        # opens a web browser to venue's websis page
        right_click = event.GetEventType() == 10035
        venue_record = self.venue_olv.GetSelectedObject()["websis"]

        if venue_record == "":
            msg_warn(self, "Venue has no websis link", self.venue_olv.GetSelectedObject()["name"])
            return

        progstring = prefs_dict["main_browser"]
        websis_prefix_string = "http://sisfm-enquiry.fm.uwa.edu.au/sisfm-enquiry/mapEnquiry/default.aspx?loc_code="
        ipstring = f'{websis_prefix_string}{venue_record}'
        _launch_main_browser(progstring, ipstring, right_click)

    def btn_timetable_evt(self, event):
        # opens a new frame for venue's timetable (grid and list views)
        sims_id = self.venue_olv.GetSelectedObject()["bookingid"]
        venue_name = self.venue_olv.GetSelectedObject()["name"]

        if not sims_id:
            msg_warn(self, "Timetable information for this venue\rhas not been made available ", venue_name)
            return

        tt_html = ac_html.timetable_html(sims_id, venue_name)

        TimeTableFrame(f"{venue_name} Timetable", tt_html, parent=self.GetParent())

    def olv_venue_keydown_evt(self, event):  # TODO rename method, split up if it makes sense
        keycode = event.GetKeyCode()
        if keycode in range(315, 318, 2):  # Checking for up & down cursor keys (315 & 317)
            self.pause_device_updating = True  # Prevents venue devices & details updating until cursor key is released

        if 91 > keycode > 47:  # this works for keys 0-9 and a-z plus a couple of others
            self.venues_search_tb.SetValue(chr(keycode).upper())
            self.venues_search_tb.SetFocus()
            self.venues_search_tb.SetInsertionPointEnd()
        event.Skip()

    def olv_venue_keyup_evt(self, event):
        keycode = event.GetKeyCode()
        if keycode in range(315, 318, 2):
            self.pause_device_updating = False
            self.olv_venue_selected_evt(self)
        elif keycode == wx.WXK_TAB:
            if not self.venue_olv.GetSelectedObject():
                # when tabbing through controls, if there is no venue selected, select/highlight the first venue
                self.olv_venue_focusselect(0)

    def olv_venue_select_none_evt(self, event):
        # doing this to clear device list if no venue is selected (eg when clicking in blank area in olv)
        self.device_olv.SetObjects([])
        self.button_group_visibility(False)
        self.update_device_count()
        # event.Skip()

    def olv_venue_selected_evt(self, _):
        if not self.pause_device_updating:
            current_venue = self.venue_olv.GetSelectedObject()
            wx.GetTopLevelParent(self).SetTitle(
                APP_NAME + "  >>  " + current_venue["name"])  # Add venue name to window title
            self.populate_device_olv(current_venue)
            self.populate_details_section(current_venue)
            self.populate_camview(current_venue)

        # event.Skip()  # Contrary to the name, event.Skip() ensures other event calls ARE executed if needed

    def olv_device_update_tooltip(self, event):
        """
        Update the tooltip on the device objectlistview
        """
        pos = wx.GetMousePosition()
        mouse_pos = self.device_olv.ScreenToClient(pos)
        item_index, flag = self.device_olv.HitTest(mouse_pos)
        if item_index != -1:
            current_device = self.device_olv.GetObjectAt(item_index)
            if current_device != self.last_device:
                self.last_device = current_device
                try:
                    cd_dp = current_device[3]
                    cd_vlan = current_device[4]
                    cd_notes = current_device[5]
                    msg = f"DP: {cd_dp}\nVLAN: {cd_vlan}\n{cd_notes}"
                    self.device_olv.SetToolTip(msg)
                except IndexError:
                    self.device_olv.SetToolTip("")
                    # Todo - currently webcam echo and PC don't have the above fields
        else:
            self.device_olv.SetToolTip("")

        event.Skip()

    def olv_device_selected_evt(self, _):
        """ This method just enables buttons dependant on the selected device """
        current_device = self.device_olv.GetSelectedObject()[0]

        if current_device.startswith(("Net", "DGX", "DVX", "DX ", "Tou")):
            apply_button_template(self.reboot_btn)
        else:
            apply_button_template(self.reboot_btn, "disabled")
        if current_device.startswith(("Net", "DGX", "DVX", "DX ", "DSP", "Key", "Vid", "Tou")):
            apply_button_template(self.telnet_btn)
        else:
            apply_button_template(self.telnet_btn, "disabled")
        if current_device.startswith(("iBoo", "LCD", "Cam", "Data", "Dis", "Pro", "WeP", "Extr", "DP ")):
            apply_button_template(self.webcontrol_btn)
        else:
            apply_button_template(self.webcontrol_btn, "disabled")
        if current_device.startswith("Tou"):
            apply_button_template(self.vnc_btn)
        else:
            apply_button_template(self.vnc_btn, "disabled")

        self.enable_group_buttons()

    """
    ### Filtering - Venues List 
    """

    def txt_venues_search_clear_evt(self, event):
        self.venue_textsearch_filter = None
        self.filter_venues_olv(None)
        event.Skip()

    def txt_venues_filter_by_search_evt(self, _):
        if self.venues_search_tb.IsEmpty():
            self.venue_textsearch_filter = None
        else:
            self.venue_textsearch_filter = Filter.TextSearch(self.venue_olv, text=self.venues_search_tb.GetValue())
            # ^ Searches for matching text in venue_olv columns

    def ckb_venues_filter_by_ctf_evt(self, event):
        choice = event.GetSelection()
        # 0 = No; 1 = Yes; 2 = Undetermined
        self.venue_olv.SortBy(1)  # Had to sort by a hidden column to remove sort icon from view, before default sort
        self.venue_olv.SetSortColumn(None)  # Setting sort column to None restores default sort order

        if choice == 1:
            self.venue_ctf_filter = Filter.Predicate(lambda x: ("Yes" in x["ctf"]))
            self.ctf_filter_ckb.SetLabelText(' CTF Venues ')
        elif choice == 0:
            self.venue_ctf_filter = Filter.Predicate(lambda x: ("Yes" not in x["ctf"]))
            self.ctf_filter_ckb.SetLabelText(' Non-CTF Venues ')
        else:
            self.venue_ctf_filter = None
            self.ctf_filter_ckb.SetLabelText(' CTF Filter: Off ')

        self.ctf_filter_ckb.Refresh()  # this method pair prevents text overlaying when it changes on layout()
        self.ctf_filter_ckb.Update()
        self.venue_olv.SetFocus()
        self.filter_venues_olv(None)

    def ckb_venues_filter_by_control_evt(self, event):
        choice = event.GetSelection()
        # 0 = No; 1 = Yes; 2 = Undetermined
        self.venue_olv.SortBy(1)
        self.venue_olv.SetSortColumn(None)

        if choice == 1:
            self.venue_ctrl_filter = Filter.Predicate(lambda x: bool(x["networkdevice"]))  # using bool for truthiness
            self.controlled_filter_ckb.SetLabelText(' Controlled Venues ')
        elif choice == 0:
            self.venue_ctrl_filter = Filter.Predicate(lambda x: (not bool(x["networkdevice"])))
            self.controlled_filter_ckb.SetLabelText(' Non-controlled Venues ')
        else:
            self.venue_ctrl_filter = None
            self.controlled_filter_ckb.SetLabelText(' Controlled Filter: Off ')

        self.controlled_filter_ckb.Refresh()
        self.controlled_filter_ckb.Update()
        self.venue_olv.SetFocus()
        self.filter_venues_olv(None)

    def filter_venues_olv(self, _):
        last_venue_selected = self.venue_olv.GetSelectedObject()
        self.venue_filter_args = []
        if self.venue_ctf_filter:
            self.venue_filter_args.append(self.venue_ctf_filter)
        if self.venue_ctrl_filter:
            self.venue_filter_args.append(self.venue_ctrl_filter)
        if self.venue_textsearch_filter:
            self.venue_filter_args.append(self.venue_textsearch_filter)
        if self.venue_filter_args:  # checking that venue_filter_args is not empty
            self.venue_olv.SetFilter(Filter.Chain(*self.venue_filter_args))
            # ^ unpacked venue_filter_args to provide arguments to Filter.Chain
        else:
            self.venue_olv.SetFilter(None)  # If there's nothing to filter, the filter is reset to None

        self.venue_olv.RepopulateList()  # Always need to repopulate after doing filter

        if last_venue_selected:
            selected_venue = self.venue_olv.FindItem(-1, last_venue_selected['name'])
            venue_index = 0 if selected_venue < 1 else selected_venue
        else:
            venue_index = 0

        self.olv_venue_focusselect(venue_index)
        self.update_venues_count()

    """
    ### Filtering - Device List 
    """

    def ckb_device_filter_toggle_evt(self, event):
        self.device_show_flagged = event.IsChecked()
        ac_utility.preferences(DATA_DIR, "update", "devicelist_show_flagged", event.IsChecked())

        self.device_olv.SetFocus()
        self.filter_devices_olv()
        # ^ possibly do this on close instead

    def filter_devices_olv(self):
        if not self.device_show_flagged:
            # filtering out any device name that starts with '*'
            self.device_olv.SetFilter(Filter.Predicate(lambda x: ("*" not in x[0])))
        else:
            self.device_olv.SetFilter(None)  # If there's nothing to filter, the filter is reset to None

        self.device_olv.RepopulateList()  # Always need to repopulate after doing filter
        self.update_device_count()

        if self.device_olv.GetItemCount():
            self.button_group_visibility(True)
            if self.autoping_active:  # this filter runs on venue_select, we might as well auto-ping on change of state
                self._run_venue_ping()
        else:
            self.button_group_visibility(False)

    """
    ### Venues Panel - Methods 
    """

    def populate_venues_olv(self):
        self.venue_olv.SetObjects(venues_full)
        self.olv_venue_focusselect(0)
        self.venue_olv.AutoSizeColumns()
        self.update_venues_count()

    def update_venues_count(self):
        self.venues_count_label.SetLabel("Venues in list: " + str(self.venue_olv.GetItemCount()))
        VenuesPanel.Layout(self)  # have to call parent's .Layout to correctly render font & alignment of the label

    def populate_device_olv(self, venue):
        self.device_olv.SetObjects(venue["networkdevice"])
        self.filter_devices_olv()

    def button_group_visibility(self, make_visible):
        exclude_buttons = [self.webcam_open_btn]
        # webcam_refresh_btn & autoping_btn are wx.ToggleButtons, not wx.Buttons, so aren't effected
        for control in self.GetChildren():
            if isinstance(control, wx.Button):
                if control not in exclude_buttons:
                    control.Show() if make_visible else control.Hide()
        self.device_olv.Select(0)

    def enable_group_buttons(self):
        # Being thorough in minimising the need to redraw the buttons - to prevent flickering
        venue_device_names = []
        for row in range(self.device_olv.GetItemCount()):
            venue_device_names.append(self.device_olv.GetItemText(row, 1))

        if "Touch Panel" or "Extron Touch Panel" in venue_device_names:
            apply_button_template(self.touchpanel_btn)
        else:
            apply_button_template(self.touchpanel_btn, "disabled")
        if "[Lectern PC]" in venue_device_names:
            apply_button_template(self.pc_btn)
        else:
            apply_button_template(self.pc_btn, "disabled")
        if "[Echo 360]" in venue_device_names:
            apply_button_template(self.echo_btn)
        else:
            apply_button_template(self.echo_btn, "disabled")

    def update_device_count(self):
        self.device_count_label.SetLabel("Devices: " + str(self.device_olv.GetItemCount()))
        # VenuesPanel.Layout(self)  # have to call parent's .Layout to correctly render font & alignment of the label

    def populate_details_section(self, venue):
        self.venue_name_text.SetLabel(venue["name"])
        self.building_name_text.SetValue(venue["building"])
        self.room_number_text.SetValue(venue["code"])
        self.capacity_text.SetValue(str(venue["capacity"]))
        self.ctf_text.SetValue(venue["ctf"])
        self.phone_text.SetValue(venue["phone"])
        self.sdc_text.SetValue(venue["sdc"])
        self.notes_text.SetValue(venue["notes"])

        self.populate_imageview(venue["websis"])

    def populate_camview(self, venue, failed=False):
        camera_type = venue["webcamtype"]
        camera_ip = venue["webcam"]
        cam_html, cam_url = None, None
        image_size_str = ""

        if camera_type:
            self.webcam_refresh_btn.SetToolTip(camera_ip)
            self.webcam_refresh_btn.Show()
            # self.webcam_open_btn.Hide()   # Hide / Show seems to work better at refreshing button text change
            self.webcam_open_btn.SetLabel(camera_type)
            self.webcam_open_btn.Refresh()  # If we don't refresh the label text usually overlays itself
            self.webcam_open_btn.Show()
            # Get the camera url

            # Todo simplify these repetitive statements also check sizing for each camera
            # Todo - also consider constructing all html in separate module

            if camera_type == "SonyCam":
                cam_url = f"http://{camera_ip}/oneshotimage.jpg"
                image_size_str = "width='352' height='230'"
            if camera_type in ["VB10", "VB50", "VB60"]:
                cam_url = f"http://{camera_ip}/-wvhttp-01-/GetOneShot?"
                image_size_str = "width='352' height='230'"
            if camera_type == "VB41":
                cam_url = f"http://{camera_ip}/-wvhttp-01-/GetOneShot?"
                image_size_str = "width='415' height='230'"

            # Will probably have to format as html similar to below and use setpage rather than loadurl
            # TODO consider saving values in prefs as a dictionary formatted as string?
            # TODO then we can edit each value in an advanced preferences dialogue rather than hard coding
            # TODO still need to condense /normalise code in this method
            # TODO next lines are placeholder until proper url is programmed
            # cam_url = "http://136.142.166.244/-wvhttp-01-/GetOneShot?"  # it's a VB60
            cam_html = "<!doctype html><meta http-equiv='X-UA-Compatible' content='IE=edge' /><html><head></head>" \
                       "<body style='margin: 0px; overflow: hidden;'><img alt='Camera Offline'" \
                f" {image_size_str} src='{cam_url}'/></body></html>"
            self.cam_html = cam_html

        else:
            # if there is no webcam....
            self.cam_html = None
            self.webcam_open_btn.Hide()
            self.webcam_refresh_btn.Hide()
            cam_image = ac_utility.random_file(str(CAM_IMAGE_DIR), [".mp4"])
            if cam_image:
                cam_html = "<!doctype html><meta http-equiv='X-UA-Compatible' content='IE=edge' /><html><head>" \
                           "<style type='text/css'>" \
                           "div{height: 210px; width: 335px; display: inline-block; " \
                           "vertical-align: top; position: relative;} " \
                           "video{max-height: 100%; max-width: 100%; width: auto; height: auto; " \
                           "position: absolute; top: 0; bottom: 0; left: 0; right: 0; margin: auto;}</style>" \
                           "<div><video autoplay loop muted playsinline>" \
                    f"<source src='file:///{str(CAM_IMAGE_DIR / cam_image)}'/></video></div>" \
                           "</head><body>" \
                           "</body></html>"

            else:
                cam_html = "<!doctype html><html><body><H1>No camera,</br>No awesome GIFs,</br>Sad..</H1></body></html>"
        if failed:
            self.cam_html = None
            cam_html = "<!doctype html><html><body>" \
                       "<H1>Camera says NO...</H1><H2>Can't connect</H2><H3>Sad...</H3>" \
                       "</body></html>"
        self.cam_viewer.SetPage(cam_html, "")

    def populate_imageview(self, websis_id):
        # default image, for when there is no building image in SIS....
        default_image = 'http://sisfm-enquiry.fm.uwa.edu.au/SISfm-Enquiry/sisdata/photos/thumb/CR/900103_1.jpg'
        websis_building_image = \
            f"http://sisfm-enquiry.fm.uwa.edu.au/SISfm-Enquiry/sisdata/photos/thumb/CR/{websis_id[:6]}_1.jpg"
        if websis_building_image:
            imageview_string = \
                "<!doctype html><meta http-equiv='X-UA-Compatible' content='IE=edge' />" \
                "<html><head><style type='text/css'> img{" \
                "display: block; " \
                "margin-left: auto; margin-right: auto; " \
                "width: 256px; max-height: 167px;" \
                "} </style></head>" \
                "<body style='margin: 8px; overflow: hidden;'><div>" \
                    f"<img src='{websis_building_image}' onerror='this.onerror=\"\"; src=\"{default_image}\";'/>" \
                "</div></body></html>"
            # !Be aware of the funky quote formatting on the img source line - it's deliberate
            #  The little bit of code will insert a default image if the called one is missing
        else:
            imageview_string = "<!doctype html><html><body><H1>Nothing to show, sad..</H1></body></html>"
        self.image_viewer.SetPage(imageview_string, "")

    def btn_autoping_toggle_evt(self, _):
        self.autoping_active = not self.autoping_active
        ac_utility.preferences(DATA_DIR, "update", "ping_on_select", self.autoping_active)
        if self.autoping_active:
            apply_button_template(self.autoping_btn, "active_toggle")
            self._run_venue_ping()  # Fires off a venue ping when enabled
        else:
            apply_button_template(self.autoping_btn, "default")

    def btn_venue_ping_evt(self, _):
        self.venue_ping_btn.Hide()
        self._run_venue_ping()
        wx.YieldIfNeeded()
        self.venue_ping_btn.Show()

    def btn_ping_evt(self, _):
        """ runs a ping on the selected device """
        # TODO at some point look at stopping multiple clicks from queuing - fixed it I think 17/2/19
        # Todo - check other buttons for the same?
        # NOTE neither enable() or show() prevent mouse event queuing - ie. clicks still register

        self.ping_btn.Hide()
        device_ip = [self.device_olv.GetSelectedObject()[1]]
        timeout = 1000
        batchsize = 1
        index = self.device_olv.GetIndexOf(self.device_olv.GetSelectedObject())
        self.device_olv.SetItem(index, 2, "")  # clears the current device ping column
        busy_cursor = wx.BusyCursor()
        result, _ = ac_ping.start(device_ip, batchsize, timeout)  # don't need the second value (process_time)
        del busy_cursor
        self.device_olv.SetItem(index, 2, result[0][1])  # populate device 'ping' column with result
        wx.YieldIfNeeded()  # Trying this to prevent extra clicks caching - seems to work well (with hidden button)
        self.ping_btn.Show()

    def _run_venue_ping(self, _=None):
        """ Runs a group ping on the visible venue devices """
        # Because we are only going to ping what is visible in the list control,
        # we aren't interested in the underlying venue_devices list
        list_count = self.device_olv.GetItemCount()
        timeout = 1000
        batchsize = prefs_dict["ping_batch_size"]
        for index in range(list_count):
            self.device_olv.SetItem(index, 2, "")  # clears the device ping column

        if list_count:
            if self.autoping_active:
                apply_button_template(self.autoping_btn, "text_alert")
                # just a visual indicator that the ping is happening
            device_ip_list = []
            # get a list of current ip addresses in device list and send to ping
            for index in range(list_count):
                device_ip_list.append(self.device_olv.GetItemText(index, 0))
            busy_cursor = wx.BusyCursor()
            result, _ = ac_ping.start(device_ip_list, batchsize, timeout)
            del busy_cursor
            # 'result' is a list of tuples [(ip, response),...] elements returned in the order sent

            # populate device list 'ping' column with results
            for index in range(list_count):
                self.device_olv.SetItem(index, 2, result[index][1])
            if self.autoping_active:
                apply_button_template(self.autoping_btn, "active_toggle")
                # a visual indicator that the ping has finished

    def olv_venue_focusselect(self, index):
        """ Move focus and then select a venue in the venue list  """
        self.venue_olv.Focus(index)
        self.venue_olv.Select(index)


###########################################################################
# Class SettingsPanel
###########################################################################

class SettingsPanel(wx.Panel):

    def __init__(self, parent):
        wx.Panel.__init__(self, parent, id=wx.ID_ANY, pos=wx.DefaultPosition, size=wx.Size(1000, 768),
                          style=wx.TAB_TRAVERSAL)

        self.SetForegroundColour(wx.Colour(COLOUR_BUTTON_TEXT_LIGHT))
        self.SetBackgroundColour(wx.Colour(COLOUR_PANEL_BG))
        self.SetMinSize(wx.Size(1000, 768))

        """
        ### Initiate empty framework for GUI elements
        """

        panel_sizer = wx.BoxSizer(wx.HORIZONTAL)

        """ Information """

        info_sizer = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY, "Info"), wx.VERTICAL)
        apply_text_template(info_sizer.GetStaticBox())

        self.htmlwin = wx.html.HtmlWindow(self, wx.ID_ANY, style=wx.NO_BORDER)

        self.htmlwin.AppendToPage("""
            <font color='white'>
            <p><b>Admin ID:</b> your 900***** staff number<ul><li>Only used for Dameware access</li></ul></p>
            <p><b>Credentials:</b> Access to Windows Credentials<ul><li>Change UWA Admin stored password</li></ul></p>           
            <p><b>Ping Timeout:</b> 1000(ms) recommended<ul><li>Altering effects Ping & AutoPing durations</li>
            <li>Too short: False Timed Out messages</li><li>Too long: Ping may be slower to finish</li></ul></p>
            <p><b>Ping Batch Size:</b> 100 is modest (1 - 2000)<ul><li>Simultaneous ping connections</li></ul></p>
            <p><b>Camera Refresh:</b> 5000(ms) is modest<ul><li>How often the webcam image updates</li></ul></p>
            <p><b>Advanced Settings:</b><ul><li>The AirTable settings should never need to be changed</li>
            <li>Unless Peter tells you to change them</li></ul></p>
            <p><b>File Locations:</b><ul><li>Chrome is the preferred Main Browser</li>
            <li>IE or Edge for the Alternative Browser</li><li>Dameware's 64bit mini-remote (DWRCC.exe)</li>
            <li>VNC: Give preference to UltraVNC</li><li>Telnet: either from the Windows\WinSxS directory</li>
            <li>or use TelnetUltra in ArseCandi's bin folder</li></ul></p>
            """)

        self.htmlwin.SetBackgroundColour(COLOUR_PANEL_BG)
        info_sizer.Add(self.htmlwin, 1, wx.EXPAND, 10)

        """ General Settings """

        mid_panel_sizer = wx.BoxSizer(wx.VERTICAL)
        general_settings_sbsizer = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY, "General Settings"), wx.HORIZONTAL)
        apply_text_template(general_settings_sbsizer.GetStaticBox())
        gen_settings_sizer = wx.BoxSizer(wx.VERTICAL)

        staffsizer_h = wx.BoxSizer()
        staffsizer_v1 = wx.BoxSizer(wx.VERTICAL)

        self.staffid_label = wx.StaticText(self, wx.ID_ANY, "Admin ID", wx.DefaultPosition, wx.DefaultSize, 0)
        staffsizer_v1.Add(self.staffid_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, 10)

        self.staffid = wx.TextCtrl(self, wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.DefaultSize, 0)
        staffsizer_v1.Add(self.staffid, 0, wx.ALL, 5)

        staffsizer_h.Add(staffsizer_v1, 0, wx.ALL, 5)

        staffsizer_v2 = wx.BoxSizer(wx.VERTICAL)

        self.credentials_button = wx.Button(self, wx.ID_ANY, "Credentials", size=wx.Size(110, 23), style=wx.NO_BORDER)
        apply_button_template(self.credentials_button)
        self.credentials_button.SetToolTip("Change Admin password locally")
        staffsizer_v2.Add(self.credentials_button, 0, wx.ALL | wx.ALIGN_BOTTOM, 5)

        staffsizer_h.Add(staffsizer_v2, 0, wx.ALL | wx.ALIGN_BOTTOM, 5)
        gen_settings_sizer.Add(staffsizer_h, 0, wx.LEFT, 0)

        pingsizer_h = wx.BoxSizer()
        pingsizer_v1 = wx.BoxSizer(wx.VERTICAL)

        self.ping_timeout_label = wx.StaticText(self, wx.ID_ANY, "Ping Timeout", wx.DefaultPosition, wx.DefaultSize, 0)
        pingsizer_v1.Add(self.ping_timeout_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, 10)

        self.ping_timeout = wx.TextCtrl(self, wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.DefaultSize, 0)
        pingsizer_v1.Add(self.ping_timeout, 0, wx.ALL, 5)

        pingsizer_h.Add(pingsizer_v1, 0, wx.ALL, 5)

        pingsizer_v2 = wx.BoxSizer(wx.VERTICAL)
        self.ping_batchsize_label = wx.StaticText(self, wx.ID_ANY, "Ping Batch Size", wx.DefaultPosition,
                                                  wx.DefaultSize, 0)

        pingsizer_v2.Add(self.ping_batchsize_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, 10)

        self.ping_batchsize = wx.TextCtrl(self, wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.DefaultSize, 0)
        pingsizer_v2.Add(self.ping_batchsize, 0, wx.ALL, 5)

        pingsizer_h.Add(pingsizer_v2, 0, wx.ALL, 5)
        gen_settings_sizer.Add(pingsizer_h, 0, wx.ALL, 0)

        camsizer_v = wx.BoxSizer(wx.VERTICAL)
        self.camera_refresh_label = wx.StaticText(self, wx.ID_ANY, "Camera Refresh", wx.DefaultPosition,
                                                  wx.DefaultSize, 0)
        camsizer_v.Add(self.camera_refresh_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, 10)

        self.camera_refresh = wx.TextCtrl(self, wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.DefaultSize, 0)
        camsizer_v.Add(self.camera_refresh, 0, wx.ALL, 5)
        gen_settings_sizer.Add(camsizer_v, 0, wx.LEFT, 5)
        #
        # """ Separation line """
        # self.sep_line1 = wx.StaticLine(self, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.LI_HORIZONTAL)
        # gen_settings_sizer.Add(self.sep_line1, 0, wx.TOP | wx.BOTTOM | wx.EXPAND, 10)

        """ Advanced Panel """
        rhs_panel_sizer = wx.BoxSizer(wx.VERTICAL)
        advanced_settings_sbsizer = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY, "Advanced Settings"), wx.HORIZONTAL)
        apply_text_template(advanced_settings_sbsizer.GetStaticBox())
        adv_settings_sizer = wx.BoxSizer(wx.VERTICAL)

        self.bearerkey_label = wx.StaticText(self, wx.ID_ANY, "AirTable Key", wx.DefaultPosition, wx.DefaultSize, 0)
        # self.bearerkey_label.Wrap(-1)
        adv_settings_sizer.Add(self.bearerkey_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, 10)

        self.bearerkey = wx.TextCtrl(self, wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.DefaultSize, 0)
        adv_settings_sizer.Add(self.bearerkey, 0, wx.ALL | wx.EXPAND, 5)

        self.airtableurl_label = wx.StaticText(self, wx.ID_ANY, "AirTable API", wx.DefaultPosition, wx.DefaultSize, 0)
        # self.airtableurl_label.Wrap(-1)
        adv_settings_sizer.Add(self.airtableurl_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, 10)

        self.airtableurl = wx.TextCtrl(self, wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.DefaultSize, 0)
        adv_settings_sizer.Add(self.airtableurl, 0, wx.ALL | wx.EXPAND, 5)

        self.airtableweb_label = wx.StaticText(self, wx.ID_ANY, "AirTable Web", wx.DefaultPosition, wx.DefaultSize, 0)
        # self.airtableweb_label.Wrap(-1)
        adv_settings_sizer.Add(self.airtableweb_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, 10)

        self.airtableweb = wx.TextCtrl(self, wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.DefaultSize, 0)
        adv_settings_sizer.Add(self.airtableweb, 0, wx.ALL | wx.EXPAND, 5)
        #
        # """ Separation line """
        # self.sep_line2 = wx.StaticLine(self, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.LI_HORIZONTAL)
        # adv_settings_sizer.Add(self.sep_line2, 0, wx.TOP | wx.BOTTOM | wx.EXPAND, 10)

        """ Button Box spacer """  # Needed to push buttons down to the bottom of the sizer
        adv_settings_sizer.Add((0, 0), 1, wx.EXPAND, 5)

        self.unlock_button = wx.Button(self, wx.ID_ANY, "Unlock", style=wx.NO_BORDER)
        apply_button_template(self.unlock_button)
        adv_settings_sizer.Add(self.unlock_button, 0, wx.ALL | wx.ALIGN_RIGHT, 5)

        """ File selectors """
        program_locations_sbsizer = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY, "Program Locations"), wx.HORIZONTAL)
        apply_text_template(program_locations_sbsizer.GetStaticBox())
        program_locations_sizer = wx.BoxSizer(wx.VERTICAL)

        self.main_browser_label = wx.StaticText(self, wx.ID_ANY, "Main Browser")
        program_locations_sizer.Add(self.main_browser_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, 6)

        self.main_browser = wx.FilePickerCtrl(self, wx.ID_ANY, wx.EmptyString, "Select the main browser location",
                                              "*.exe", wx.DefaultPosition, wx.DefaultSize,
                                              wx.FLP_DEFAULT_STYLE | wx.FLP_FILE_MUST_EXIST | wx.FLP_SMALL)
        self.main_browser.SetInitialDirectory("C:")
        self.main_browser.SetBackgroundColour(COLOUR_PANEL_BG)
        program_locations_sizer.Add(self.main_browser, 0, wx.ALL | wx.EXPAND, 5)

        self.alt_browser_label = wx.StaticText(self, wx.ID_ANY, "Alternative Browser")
        program_locations_sizer.Add(self.alt_browser_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, 6)

        self.alt_browser = wx.FilePickerCtrl(self, wx.ID_ANY, wx.EmptyString, "Select the alternative browser location",
                                             "*.exe", wx.DefaultPosition, wx.DefaultSize,
                                             wx.FLP_DEFAULT_STYLE | wx.FLP_FILE_MUST_EXIST | wx.FLP_SMALL)
        self.alt_browser.SetInitialDirectory("C:")
        self.alt_browser.SetBackgroundColour(COLOUR_PANEL_BG)
        program_locations_sizer.Add(self.alt_browser, 0, wx.ALL | wx.EXPAND, 5)

        self.dameware_label = wx.StaticText(self, wx.ID_ANY, "Dameware(v10)")
        program_locations_sizer.Add(self.dameware_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, 6)

        self.dameware = wx.FilePickerCtrl(self, wx.ID_ANY, wx.EmptyString,
                                          "Select the Dameware mini remote control location", "*.exe",
                                          wx.DefaultPosition, wx.DefaultSize,
                                          wx.FLP_DEFAULT_STYLE | wx.FLP_FILE_MUST_EXIST | wx.FLP_SMALL)
        self.dameware.SetInitialDirectory("C:")
        program_locations_sizer.Add(self.dameware, 0, wx.ALL | wx.EXPAND, 5)

        self.shure_label = wx.StaticText(self, wx.ID_ANY, "Wireless Workbench 6")
        program_locations_sizer.Add(self.shure_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, 6)

        self.shure = wx.FilePickerCtrl(self, wx.ID_ANY, wx.EmptyString,
                                       "Select the Wireless Workbench 6 (64bit) location", "*.exe",
                                       wx.DefaultPosition, wx.DefaultSize,
                                       wx.FLP_DEFAULT_STYLE | wx.FLP_FILE_MUST_EXIST | wx.FLP_SMALL)
        self.shure.SetInitialDirectory("C:")
        program_locations_sizer.Add(self.shure, 0, wx.ALL | wx.EXPAND, 5)

        self.vnc_label = wx.StaticText(self, wx.ID_ANY, "VNC")
        program_locations_sizer.Add(self.vnc_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, 6)

        self.vnc = wx.FilePickerCtrl(self, wx.ID_ANY, wx.EmptyString, "Select the VNC program location", "*.exe",
                                     wx.DefaultPosition, wx.DefaultSize,
                                     wx.FLP_DEFAULT_STYLE | wx.FLP_FILE_MUST_EXIST | wx.FLP_SMALL)
        self.vnc.SetInitialDirectory("C:")
        program_locations_sizer.Add(self.vnc, 0, wx.ALL | wx.EXPAND, 5)

        self.telnet_label = wx.StaticText(self, wx.ID_ANY, "Telnet")
        program_locations_sizer.Add(self.telnet_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, 6)

        self.telnet = wx.FilePickerCtrl(self, wx.ID_ANY, wx.EmptyString, "Select the TelnetUltra program location",
                                        "*.exe", wx.DefaultPosition, wx.DefaultSize,
                                        wx.FLP_DEFAULT_STYLE | wx.FLP_FILE_MUST_EXIST | wx.FLP_SMALL)
        self.telnet.SetInitialDirectory("C:")
        program_locations_sizer.Add(self.telnet, 0, wx.ALL | wx.EXPAND, 5)

        """ Page Buttons """
        button_sizer = wx.BoxSizer(wx.HORIZONTAL)

        self.default_button = wx.Button(self, wx.ID_ANY, "Defaults", wx.DefaultPosition, wx.DefaultSize, wx.NO_BORDER)
        self.default_button.SetToolTip("Fills default values in all fields")
        apply_button_template(self.default_button)
        button_sizer.Add(self.default_button, 0, wx.ALL, 5)

        self.save_button = wx.Button(self, wx.ID_ANY, "Save", wx.DefaultPosition, wx.DefaultSize, wx.NO_BORDER)
        self.save_button.SetToolTip("Save changes and exit")
        apply_button_template(self.save_button)
        button_sizer.Add(self.save_button, 0, wx.ALL, 5)

        self.cancel_button = wx.Button(self, wx.ID_ANY, "Cancel", wx.DefaultPosition, wx.DefaultSize, wx.NO_BORDER)
        self.cancel_button.SetToolTip("Cancel changes and exit")
        apply_button_template(self.cancel_button)
        button_sizer.Add(self.cancel_button, 0, wx.ALL, 5)

        for control in self.GetChildren():
            if isinstance(control, wx.StaticText):
                apply_text_template(control, "details_text")

        for control in self.GetChildren():
            if isinstance(control, wx.FilePickerCtrl):
                control.SetBackgroundColour(COLOUR_PANEL_BG)

        general_settings_sbsizer.Add(gen_settings_sizer, 1, wx.ALL | wx.EXPAND, 5)
        advanced_settings_sbsizer.Add(adv_settings_sizer, 1, wx.ALL | wx.EXPAND, 5)
        program_locations_sbsizer.Add(program_locations_sizer, 1, wx.ALL | wx.EXPAND, 5)

        mid_panel_sizer.Add(general_settings_sbsizer, 1, wx.ALL | wx.EXPAND, 0)
        mid_panel_sizer.Add(advanced_settings_sbsizer, 1, wx.ALL | wx.EXPAND, 0)
        rhs_panel_sizer.Add(program_locations_sbsizer, 1, wx.ALL | wx.EXPAND, 0)
        rhs_panel_sizer.Add(button_sizer, 0, wx.TOP | wx.LEFT | wx.ALIGN_RIGHT, 5)

        panel_sizer.Add(info_sizer, 1, wx.ALL | wx.EXPAND, 5)
        panel_sizer.Add(mid_panel_sizer, 1, wx.ALL | wx.EXPAND, 5)
        panel_sizer.Add(rhs_panel_sizer, 2, wx.ALL | wx.EXPAND, 5)

        self.SetSizer(panel_sizer)
        self.Layout()

        """
        ### Setup event binding connections
        """

        self.Bind(wx.EVT_SHOW, self.populate_preferences_evt)
        self.unlock_button.Bind(wx.EVT_BUTTON, self.unlock_button_evt)
        self.credentials_button.Bind(wx.EVT_BUTTON, self.credentials_button_evt)
        self.save_button.Bind(wx.EVT_BUTTON, self.save_settings_button_evt)
        self.cancel_button.Bind(wx.EVT_BUTTON, self.cancel_settings_button_evt)
        self.default_button.Bind(wx.EVT_BUTTON, self.default_settings_button_evt)

    """
    ### Settings Panel Class -  event handlers 
    """

    def populate_preferences_evt(self, _):
        # Bound to the Show event. If app is quit while on this panel, prevent it firing by checking that .self exists
        if self:
            self._dict_to_fields(prefs_dict)

            # Disable advanced settings by default
            self.bearerkey.Enable(False)
            self.airtableurl.Enable(False)
            self.airtableweb.Enable(False)

    def _dict_to_fields(self, d: dict):
        self.staffid.SetValue(d.get("staff_id", '900xxxxx'))
        self.ping_timeout.SetValue(str(d.get("ping_timeout", 1000)))
        self.ping_batchsize.SetValue(str(d.get("ping_batch_size", 100)))
        self.camera_refresh.SetValue(str(d.get("camera_refresh", 5000)))
        self.main_browser.SetPath(d["main_browser"])
        self.alt_browser.SetPath(d["alt_browser"])
        self.dameware.SetPath(d["dameware"])
        self.shure.SetPath(d["shure"])
        self.vnc.SetPath(d["vnc"])
        self.telnet.SetPath(d["telnet"])
        self.bearerkey.SetValue(d["bearer_key"])
        self.airtableurl.SetValue(d["airtable_url"])
        self.airtableweb.SetValue(d["airtable_web"])

    def unlock_button_evt(self, _):
        secure_fields = [self.bearerkey, self.airtableurl, self.airtableweb]
        for field in secure_fields:
            field.Enable(True)
        filename = str(RESOURCE_DIR) + "/audio/llamas.wav"
        sound = Sound(filename)
        if sound.IsOk():
            sound.Play(1)
        else:
            wx.MessageBox("Invalid sound file", "Error")
        del sound
        msg_warn(self, "Be very careful, choosing bad values may\nlock out the program", "! Danger Wil Robinson !")

    def credentials_button_evt(self, _):
        try:
            # C:\Windows\System32\control.exe /name Microsoft.CredentialManager

            # Resetting>  "runas.exe /savecred /user:uniwa\"
            # + Preferences.UserAccountID + " """ + Preferences.Dameware + " -c: -m:"""

            # Hoping that the 90042923 can be fixed with credential manager

            subprocess.Popen(['C:\\Windows\\System32\\control.exe', '/name', 'Microsoft.CredentialManager'])
            # opens Windows 10 Credential manager
        except OSError as e:
            print("Credential Manager failed to run:", e)
            msg_warn(self, f"Credential Manager failed to run")

    def save_settings_button_evt(self, _):
        ac_utility.preferences(DATA_DIR, "update", "staff_id", self.staffid.GetValue())
        ac_utility.preferences(DATA_DIR, "update", "camera_refresh", int(self.camera_refresh.GetValue()))
        ac_utility.preferences(DATA_DIR, "update", "ping_timeout", int(self.ping_timeout.GetValue()))
        ac_utility.preferences(DATA_DIR, "update", "main_browser", self.main_browser.GetPath())
        ac_utility.preferences(DATA_DIR, "update", "alt_browser", self.alt_browser.GetPath())
        ac_utility.preferences(DATA_DIR, "update", "dameware", self.dameware.GetPath())
        ac_utility.preferences(DATA_DIR, "update", "shure", self.shure.GetPath())
        ac_utility.preferences(DATA_DIR, "update", "vnc", self.vnc.GetPath())
        ac_utility.preferences(DATA_DIR, "update", "telnet", self.telnet.GetPath())
        ac_utility.preferences(DATA_DIR, "update", "bearer_key", self.bearerkey.GetValue())
        ac_utility.preferences(DATA_DIR, "update", "airtable_url", self.airtableurl.GetValue())
        ac_utility.preferences(DATA_DIR, "update", "airtable_web", self.airtableweb.GetValue())
        ac_utility.preferences(DATA_DIR, "update", "ping_batch_size", int(self.ping_batchsize.GetValue()))

        # reload the preferences from the file on disc
        global prefs_dict
        prefs_dict = ac_utility.preferences(DATA_DIR)

        # The method below calls the method handler directly, passing the appropriate item id to switch to main panel
        MainFrame.switch_panel(self.GetParent(),
                               wx.CommandEvent(wx.EVT_MENU.typeId, self.GetParent().main_item.GetId()))

    def cancel_settings_button_evt(self, _):
        MainFrame.switch_panel(self.GetParent(),
                               wx.CommandEvent(wx.EVT_MENU.typeId, self.GetParent().main_item.GetId()))

    def default_settings_button_evt(self, _):
        self._dict_to_fields(ac_utility.DEFAULT_PREFS)


###########################################################################
# Class Statistics Report
###########################################################################


class StatisticsReport(wx.Panel):

    def __init__(self, parent):
        wx.Panel.__init__(self, parent, id=wx.ID_ANY, pos=wx.DefaultPosition, size=wx.Size(1000, 768),
                          style=wx.TAB_TRAVERSAL)

        self.SetForegroundColour(wx.Colour(COLOUR_BUTTON_TEXT_LIGHT))
        self.SetBackgroundColour(wx.Colour(COLOUR_PANEL_BG))
        self.SetMinSize(wx.Size(1000, 768))

        panel_sizer = wx.BoxSizer(wx.HORIZONTAL)

        info_sizer = wx.BoxSizer(wx.VERTICAL)

        self.branding = wx.StaticText(self, wx.ID_ANY, APP_NAME, wx.DefaultPosition, wx.DefaultSize,
                                      wx.ALIGN_CENTRE)
        self.branding.Wrap(-1)
        self.branding.SetFont(
            wx.Font(22, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD, False, "Segoe UI Semibold"))
        self.branding.SetForegroundColour(wx.Colour(255, 128, 0))
        self.branding.SetBackgroundColour(wx.Colour(128, 0, 0))
        self.branding.SetMinSize(wx.Size(200, 50))

        info_sizer.Add(self.branding, 0, wx.ALIGN_CENTER | wx.ALL, 20)

        self.version_text = wx.StaticText(self, wx.ID_ANY, f"Version info:\n{BUILD_VER} (beta)",
                                          wx.DefaultPosition, wx.DefaultSize, wx.ALIGN_CENTRE)
        self.version_text.Wrap(-1)
        info_sizer.Add(self.version_text, 0, wx.ALIGN_CENTER | wx.ALL, 5)

        self.info_text = wx.StaticText(self, wx.ID_ANY, f"AirTable data last changed:\n"
        f"{ac_utility.get_file_timestamp(DATA_DIR / 'icandi.json')}",
                                       wx.DefaultPosition, wx.DefaultSize, wx.ALIGN_CENTRE)
        self.info_text.Wrap(-1)
        self.info_text.SetFont(
            wx.Font(10, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL, False, wx.EmptyString))
        self.info_text.SetMinSize(wx.Size(400, -1))

        info_sizer.Add(self.info_text, 0, wx.ALIGN_CENTER | wx.ALL, 10)

        panel_sizer.Add(info_sizer, 0, wx.ALIGN_CENTER, 5)

        stats_box_sizer = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY, "Statistical Summary"), wx.VERTICAL)
        apply_text_template(stats_box_sizer.GetStaticBox())

        stats_table_sizer = wx.BoxSizer(wx.HORIZONTAL)

        stats = arsecandi.get_venue_stats(venues_full)

        self.htmlwin = wx.html.HtmlWindow(self, wx.ID_ANY, style=wx.NO_BORDER)

        # Todo - again, consider html construction in another module

        self.htmlwin.AppendToPage(f"""
            <font color='white'>
            <table border=0 cellpadding=10 bgcolor={COLOUR_TABLE_BG}>
                <thead>
                    <tr bgcolor={COLOUR_TABLE_HEADER_BG}>
                        <th align=right width=123></th>
                        <th width=100> CTF </th>
                        <th width=100>Non-CTF</th>
                        <th width=100>Totals</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <th scope='row' align='right' bgcolor={COLOUR_TABLE_HEADER_BG}>Venue Type</th>
                        <td align=center>{stats["ctf_y"]}</td>
                        <td align=center>{stats["ctf_n"]}</td>
                        <td align=center>{stats["ctf_tot"]}</td>
                    </tr>
                    <tr>
                        <th scope='row' align='right' bgcolor={COLOUR_TABLE_HEADER_BG}>Lecturn PC</th>
                        <td align=center>{stats["ctf_y_pc"]}</td>
                        <td align=center>{stats["ctf_n_pc"]}</td>
                        <td align=center>{stats["ctf_tot_pc"]}</td>
                    </tr>
                    <tr>
                        <th scope='row' align='right' bgcolor={COLOUR_TABLE_HEADER_BG}>Web Camera</th>
                        <td align=center>{stats["ctf_y_cam"]}</td>
                        <td align=center>{stats["ctf_n_cam"]}</td>
                        <td align=center>{stats["ctf_tot_cam"]}</td>
                    </tr>
                    <tr>
                        <th scope='row' align='right' bgcolor={COLOUR_TABLE_HEADER_BG}>Echo Device</th>
                        <td align=center>{stats["ctf_y_echo"]}</td>
                        <td align=center>{stats["ctf_n_echo"]}</td>
                        <td align=center>{stats["ctf_tot_echo"]}</td>
                    </tr>
                </tbody>
            </table>

            <p></p>
            <table border=0 cellpadding=10 bgcolor={COLOUR_TABLE_BG}>
                <thead>
                    <tr bgcolor={COLOUR_TABLE_HEADER_BG}>
                        <th colspan=6>Venue Web Cameras</th>
                    </tr>
                </thead>
                <tbody>
                    <tr bgcolor={COLOUR_TABLE_HEADER_BG}>
                        <th width=70>VB10</th>
                        <th width=70>VB41</th>
                        <th width=70>VB50</th>
                        <th width=70>VB60</th>
                        <th width=70>Sony</th>
                        <th width=70>Total</th>
                    </tr>
                    <tr>
                        <td align=center>{stats["camtype_vb10"]}</td>
                        <td align=center>{stats["camtype_vb41"]}</td>
                        <td align=center>{stats["camtype_vb50"]}</td>
                        <td align=center>{stats["camtype_vb60"]}</td>
                        <td align=center>{stats["camtype_sony"]}</td>
                        <td align=center>{stats["camtype_tot"]}</td>
                    </tr>
                </tbody>
            </table>

            <p></p>
            <table border=0 cellpadding=10 bgcolor={COLOUR_TABLE_BG}>
                <thead>
                    <tr bgcolor={COLOUR_TABLE_HEADER_BG}>
                        <th colspan=2>Venue Device IP Allocations</th>
                    </tr>
                </thead>
                <tbody>
                    <tr bgcolor={COLOUR_TABLE_HEADER_BG}>
                        <th width=214>Allocated IP Addresses</th>
                        <th width=214>Active IP Addresses</th>
                    </tr>
                    <tr>
                        <td align=center>{stats["ip_alloc_tot"]}</td>
                        <td align=center>{stats["ip_active_alloc_tot"]}</td>
                    </tr>
                </tbody>
            </table>
            """)

        self.htmlwin.SetBackgroundColour(COLOUR_PANEL_BG)
        stats_table_sizer.Add(self.htmlwin, 1, wx.EXPAND, 10)

        stats_box_sizer.Add(stats_table_sizer, 1, wx.ALIGN_CENTER | wx.ALL | wx.EXPAND, 5)
        panel_sizer.Add(stats_box_sizer, 2, wx.ALIGN_CENTER | wx.ALL | wx.EXPAND, 10)

        self.SetSizer(panel_sizer)
        self.Layout()


###########################################################################
# Class WebCam Frame
###########################################################################


class WebCamFrame(wx.Frame):
    """"""

    def __init__(self, title, size, address, parent=None):
        """Constructor"""
        wx.Frame.__init__(self, parent=parent, title=title, size=size)

        # # TODO - give up on this and just use browser window & alt browser on button
        # # todo OR try using exit and bound close methods like MainFrame - might be better
        # # Might have to wrap the viewer in html like I did on the webcam image viewer?

        self.SetSizeHints(size, size)

        frame_sizer = wx.BoxSizer(wx.VERTICAL)

        self.main_panel = wx.Panel(self, wx.ID_ANY, wx.DefaultPosition, size, wx.TAB_TRAVERSAL)
        panel_sizer = wx.BoxSizer(wx.VERTICAL)

        # default_image = 'http://sisfm-enquiry.fm.uwa.edu.au/SISfm-Enquiry/sisdata/photos/thumb/CR/900103_1.jpg'

        self.cam_viewer = wx.html2.WebView.New(self.main_panel, wx.ID_ANY, address, wx.DefaultPosition, size)

        panel_sizer.Add(self.cam_viewer, 1, wx.ALL)

        self.main_panel.SetSizer(panel_sizer)
        self.main_panel.Layout()
        panel_sizer.Fit(self.main_panel)
        frame_sizer.Add(self.main_panel, 1, wx.EXPAND | wx.ALL)

        self.SetSizer(frame_sizer)
        self.Layout()

        self.Centre(wx.BOTH)
        self.Show()

        self.Bind(wx.EVT_CLOSE, self.i_stop_now)

    def i_stop_now(self, evt):
        self.Destroy()
        evt.Skip()


###########################################################################
# Class TimeTable Frame
###########################################################################


class TimeTableFrame(wx.Frame):
    """"""

    def __init__(self, title, tt_html, parent=None):
        """Constructor"""
        self.tt_html = tt_html
        self.current_content = 0

        wx.Frame.__init__(self, parent=parent, title=title, size=wx.Size(1200, 480))

        self.SetSizeHints((1200, 480), wx.DefaultSize)
        # self.SetMinSize(wx.Size(1412, 840))

        frame_sizer = wx.BoxSizer(wx.HORIZONTAL)

        self.main_panel = wx.Panel(self, wx.ID_ANY, wx.DefaultPosition, wx.Size(1200, 480))
        self.main_panel.SetMinSize(wx.Size(1200, 480))

        panel_sizer = wx.BoxSizer(wx.VERTICAL)

        # panel_sizer.AddStretchSpacer()

        self.view_btn = wx.Button(self.main_panel, wx.ID_ANY, "Change View", wx.DefaultPosition, wx.DefaultSize, 0)
        panel_sizer.Add(self.view_btn, 0, wx.ALIGN_CENTER_HORIZONTAL | wx.ALL, 5)

        self.tt_viewer = wx.html2.WebView.New(self.main_panel, size=wx.Size(1200, 480))
        self.tt_viewer.SetMinSize(wx.Size(1200, 480))

        self.tt_viewer.SetPage(self.tt_html[self.current_content], "")
        # self.tt_viewer.SetPage(list_html, "")

        panel_sizer.Add(self.tt_viewer, 2, wx.ALIGN_CENTER | wx.EXPAND | wx.ALL)

        self.tt_viewer.Enable(True)
        # panel_sizer.Add((0, 0), 1, wx.EXPAND, 5)

        # panel_sizer.AddStretchSpacer()
        self.main_panel.SetSizer(panel_sizer)
        self.main_panel.Layout()
        # panel_sizer.Fit(self.main_panel)
        frame_sizer.Add(self.main_panel, 1, wx.EXPAND | wx.ALL)

        self.SetSizer(frame_sizer)
        self.Layout()

        self.Centre(wx.BOTH)
        self.Show()

        """
        ### Setup event binding connections
        """

        self.view_btn.Bind(wx.EVT_BUTTON, self.btn_view_evt)

    def btn_view_evt(self, event):
        self.current_content = not self.current_content
        self.tt_viewer.SetPage(self.tt_html[self.current_content], "")
        self.Layout()
        event.Skip()


###########################################################################
# Class MainFrame
###########################################################################

class MainFrame(wx.Frame):

    def __init__(self, parent):
        wx.Frame.__init__(self, parent, id=wx.ID_ANY, title=APP_NAME, pos=wx.DefaultPosition,
                          size=wx.Size(-1, -1), style=wx.DEFAULT_FRAME_STYLE | wx.TAB_TRAVERSAL)
        win_width, win_height = prefs_dict["win_size"]
        win_max = prefs_dict["win_max"]
        self.SetSizeHints(wx.DefaultSize, wx.DefaultSize)
        self.SetIcon(wx.Icon(str(RESOURCE_DIR) + "/64-Candy-icon.png", wx.BITMAP_TYPE_PNG))
        self.SetMinSize(wx.Size(1412, 768))
        if not win_max:
            self.SetSize(win_width, win_height)
        else:
            self.Maximize()
            self.SetSize(win_width, win_height)
        sizer = wx.BoxSizer()

        # Tooltip delays seem to be across the app (not window/button specific)
        wx.ToolTip.SetDelay(800)
        wx.ToolTip.SetAutoPop(4000)

        self.main_panel = VenuesPanel(self)
        sizer.Add(self.main_panel, 1, wx.EXPAND, 5)
        self.settings_panel = SettingsPanel(self)
        sizer.Add(self.settings_panel, 1, wx.EXPAND, 5)
        self.online_report = StatisticsReport(self)
        sizer.Add(self.online_report, 1, wx.EXPAND, 5)
        self.settings_panel.Hide()
        self.online_report.Hide()

        self.SetSizer(sizer)
        self.Centre(wx.BOTH)
        self.SetPosition(prefs_dict["win_pos"])
        self.Layout()

        """
        ### Setup menu bar
        """
        menubar = wx.MenuBar()  # instantiate a MenuBar object
        menubar.SetBackgroundColour(wx.SystemSettings.GetColour(wx.SYS_COLOUR_BTNFACE))
        self.file = wx.Menu()  # instantiate a Menu object
        self.tools = wx.Menu()
        self.view = wx.Menu()

        # instantiate a Menu Item object and add to Menu
        self.main_item = wx.MenuItem(self.file, wx.ID_ANY, "&Main", "View main window", wx.ITEM_NORMAL)
        self.view.Append(self.main_item)
        self.main_item.Enable(False)
        self.settings_item = wx.MenuItem(self.file, wx.ID_ANY, "&Settings", "View or Change ArseCandi options",
                                         wx.ITEM_NORMAL)
        self.view.Append(self.settings_item)
        self.report_item = wx.MenuItem(self.file, wx.ID_ANY, "Stats &Report", "A few statistics", wx.ITEM_NORMAL)
        self.view.Append(self.report_item)
        self.view.AppendSeparator()  # add a separator to Menu
        self.view.Append(wx.ID_ABOUT, "About")

        self.refresh_item = wx.MenuItem(self.file, wx.ID_ANY, "&Refresh", "Refresh data from AirTable", wx.ITEM_NORMAL)
        self.file.Append(self.refresh_item)
        self.file.AppendSeparator()
        exit_item = wx.MenuItem(self.file, wx.ID_EXIT, "&Exit", wx.EmptyString, wx.ITEM_NORMAL)
        self.file.Append(exit_item)

        self.timetable_item = wx.MenuItem(self.file, wx.ID_ANY, "&Timetable", "Timetable Website", wx.ITEM_NORMAL)
        self.tools.Append(self.timetable_item)
        self.booker_item = wx.MenuItem(self.file, wx.ID_ANY, "&Resource Booker", "Resource Booker Website",
                                       wx.ITEM_NORMAL)
        self.tools.Append(self.booker_item)
        self.tools.AppendSeparator()
        self.echo_item = wx.MenuItem(self.file, wx.ID_ANY, "&Echo 360", "Echo 360 Monitor", wx.ITEM_NORMAL)
        self.tools.Append(self.echo_item)
        self.workbench_item = wx.MenuItem(self.file, wx.ID_ANY, "&Wireless Workbench", "Shure Wireless Workbench 6",
                                          wx.ITEM_NORMAL)
        self.tools.Append(self.workbench_item)

        menubar.Append(self.file, "&File")  # add Menu object to MenuBar object
        menubar.Append(self.tools, "&Tools")
        menubar.Append(self.view, "&View")

        self.SetMenuBar(menubar)  # add MenuBar object to MainFrame

        """
        ### Setup status bar
        """
        self.status_bar = self.CreateStatusBar(3, wx.STB_SIZEGRIP, wx.ID_ANY)
        self.status_bar.SetStatusWidths([-1, 274, 274])
        self.status_bar.SetBackgroundColour(wx.Colour(COLOUR_TEXT_LABELS))
        self.status_bar.SetForegroundColour(wx.Colour(COLOUR_TEXT_LABELS))
        self.PushStatusText(f'Current data date: {ac_utility.get_file_timestamp(DATA_DIR / "icandi.json")}', 1)
        last_update_time = time.strftime('%d %b %Y %H:%M:%S', prefs_dict["last_data_refresh"])
        self.PushStatusText(f'Last checked for updates: {last_update_time}', 2)
        self.status_bar.Enable(False)

        """
        ### Setup event binding connections
        """
        # Bind a MenuEvent (clicking the exit_item) to the method quit_app
        # self.Bind(wx.EVT_MENU, self.Close, id=exit_item.GetId())
        self.Bind(wx.EVT_MENU, self.quit_app, id=exit_item.GetId())
        self.Bind(wx.EVT_MENU, self.refresh_menu_evt, id=self.refresh_item.GetId())
        self.Bind(wx.EVT_MENU, self.switch_panel, id=self.settings_item.GetId())
        self.Bind(wx.EVT_MENU, self.switch_panel, id=self.main_item.GetId())
        self.Bind(wx.EVT_MENU, self.switch_panel, id=self.report_item.GetId())
        self.Bind(wx.EVT_MENU, self.timetable_menu_evt, id=self.timetable_item.GetId())
        self.Bind(wx.EVT_MENU, self.booker_menu_evt, id=self.booker_item.GetId())
        self.Bind(wx.EVT_MENU, self.echo_menu_evt, id=self.echo_item.GetId())
        self.Bind(wx.EVT_MENU, self.workbench_menu_evt, id=self.workbench_item.GetId())
        self.Bind(wx.EVT_MENU, on_about, id=wx.ID_ABOUT)
        self.Bind(wx.EVT_CLOSE, self.close_n_tidy)
        self.status_bar.Bind(wx.EVT_LEFT_DOWN, self.status_click_evt)

        # Once the Main Panel has been drawn and populated, we can run a check to see if the data needs refreshing
        # This is done by comparing the AirTable JSON with the JSON we've just used to populate the app
        if bg_refresh_permitted(update_has_run):
            self.refresh_data()

    def switch_panel(self, event):
        main_sel = event.GetId() == self.main_item.GetId()
        settings_sel = event.GetId() == self.settings_item.GetId()
        report_sel = event.GetId() == self.report_item.GetId()
        if report_sel:
            self.SetTitle("Status Report")
        elif settings_sel:
            self.SetTitle("Settings and Preferences")
        else:
            self.SetTitle(APP_NAME)

        self.main_item.Enable(not main_sel)
        self.settings_item.Enable(not settings_sel)
        self.report_item.Enable(not report_sel)

        self.settings_panel.Show(settings_sel)
        self.online_report.Show(report_sel)
        self.main_panel.Show(main_sel)
        self.Layout()

    def close_n_tidy(self, event):
        # Preserving window metrics in preferences for next start-up
        maxed = self.IsMaximized()
        win_x, win_y = self.GetPosition()
        width, height = self.GetSize()
        # The following doesn't seem to be needed on an extended desktop
        # win_monitor = wx.Display.GetFromWindow(self)
        # print(win_x, win_y, width, height, maxed, win_monitor)
        ac_utility.preferences(DATA_DIR, "update", "win_max", maxed)
        if not maxed:
            ac_utility.preferences(DATA_DIR, "update", "win_pos", (win_x, win_y))
            ac_utility.preferences(DATA_DIR, "update", "win_size", (width, height))
        else:
            ac_utility.preferences(DATA_DIR, "update", "win_pos",
                                   (win_x + 25, win_y + 25))  # +25 fix autohide top taskbar

        self.main_panel.Hide()  # for some reason raises c++ assert error if this panel still shows when closing?!?!
        self.main_panel.timer.Stop()  # Ensure the webcam monitor timer is stopped before exit
        del self.main_panel.timer  # precaution only - don't think it matters

        event.Skip()

    def timetable_menu_evt(self, _):
        # opens a web browser to the UWA Venue Timetable page
        progstring = prefs_dict["main_browser"]
        ipstring = prefs_dict["timetable_url"]
        _launch_main_browser(progstring, ipstring)

    def booker_menu_evt(self, _):
        # opens a web browser to the UWA Resource Booker page
        progstring = prefs_dict["main_browser"]
        ipstring = prefs_dict["res_booker_url"]
        _launch_main_browser(progstring, ipstring)

    def echo_menu_evt(self, _):
        # opens a web browser to the UWA Venue Timetable  page
        progstring = prefs_dict["main_browser"]
        ipstring = prefs_dict["echo_monitor_url"]
        _launch_main_browser(progstring, ipstring)

    def workbench_menu_evt(self, _):
        progstring = prefs_dict["shure"]
        try:
            subprocess.Popen([progstring])
            # opens Wireless Workbench 6 ( takes no parameters )
        except OSError as e:
            print("Wireless Workbench 6 failed to run:", e)
            msg_warn(self, f"Wireless Workbench 6 failed to run:\n{progstring}\n\nCheck: View -> Settings\n\n{e}")
        pass

    def refresh_menu_evt(self, _):
        if self.status_bar.GetStatusText(2).startswith("Last checked"):
            self.refresh_data()

    def refresh_data(self):
        prev_sb1_text = self.status_bar.GetStatusText(1)
        self.PopStatusText(1)
        prev_sb2_text = self.status_bar.GetStatusText(2)
        self.PopStatusText(2)
        self.PushStatusText("ArseCandi: Checking for updates", 2)

        startWorker(self._process_update, self._run_silent_update, cargs=(prev_sb1_text, prev_sb2_text,), jobID=6969)

    def _run_silent_update(self):
        results = arsecandi.get_venue_list(DATA_DIR, True)  # results => (venues_full_tmp, update_ready, failed_msg)
        return results

    def _process_update(self, worker_fn, prv_sb1_text, prv_sb2_text):
        global venues_full

        def _restore_status_text(sb1_text, sb2_text):
            # Reset the status bar text to what it was before trying to update
            self.PushStatusText(sb1_text, 1)
            self.PopStatusText(2)
            self.PushStatusText(sb2_text, 2)

        venues_full_tmp, update_ready, failed_msg = worker_fn.get()

        if failed_msg:
            msg_warn(self, failed_msg)
            _restore_status_text(prv_sb1_text, prv_sb2_text)

        else:
            if update_ready:
                venues_full = venues_full_tmp
                self.PopStatusText(2)
                self.PushStatusText("New data available: click to update", 2)
                self.status_bar.Enable()
            else:
                current_time = time.strftime('%d %b %Y %H:%M:%S', time.localtime())
                _restore_status_text(prv_sb1_text, f'Last checked for updates: {current_time}')

    def _push_new_data(self):
        self.main_panel.venue_olv.SetObjects(venues_full, True)

        # this is just to scroll the last selected venue into view (if needed)
        if not self.main_panel.venue_olv.GetSelectedObject():
            self.main_panel.olv_venue_focusselect(0)
        else:
            s_obj = self.main_panel.venue_olv.GetSelectedObject()
            i_obj = self.main_panel.venue_olv.GetIndexOf(s_obj)
            self.main_panel.venue_olv.EnsureCellVisible(i_obj, 0)

        current_time = time.strftime('%d %b %Y %H:%M:%S', time.localtime())
        current_data_date = ac_utility.get_file_timestamp(DATA_DIR / "icandi.json")
        self.PopStatusText(2)
        self.PushStatusText(f"Current data date: {current_data_date}", 1)
        self.PushStatusText(f"Last checked for updates: {current_time}", 2)

    def status_click_evt(self, _):
        self._push_new_data()
        self.status_bar.Enable(False)

    # Quits the frame... closing the window / app
    def quit_app(self, _):
        self.Close()


"""
### GUI - widget formatting Methods 
"""


def apply_button_template(button: wx.AnyButton, style="default"):
    """ Styles: default; active_toggle; text_alert; disabled"""

    fnt = button.GetFont()
    if style == "default":  # Default style for any button
        fnt.SetPointSize(APP_FS + 1)
        fnt.SetWeight(wx.FONTWEIGHT_BOLD)
        button.SetBackgroundColour(COLOUR_BUTTON_DEFAULT)
        button.SetForegroundColour(COLOUR_BUTTON_TEXT_LIGHT)
        button.Enable(True)
    elif style == "active_toggle":  # A style for an active toggle button
        fnt.SetPointSize(APP_FS + 1)
        fnt.SetWeight(wx.FONTWEIGHT_BOLD)
        button.SetBackgroundColour(wx.SystemSettings.GetColour(wx.SYS_COLOUR_BTNFACE))
        button.SetForegroundColour(COLOUR_BUTTON_TEXT_ACTIVE)
    elif style == "text_alert":
        button.SetForegroundColour(COLOUR_BUTTON_TEXT_ALERT)
    elif style == "disabled":
        button.SetBackgroundColour(COLOUR_BUTTON_DISABLED)
        button.SetForegroundColour(COLOUR_BUTTON_TEXT_DISABLED)
        button.Enable(False)  # System overrides text colour setting when button disabled

    button.SetFont(fnt)


def apply_text_template(text: wx.TEXT_TYPE_ANY, style="stb_default"):
    """ Styles: stb_default; details_label; details_venue_name; details_text """

    fnt = text.GetFont()
    if style == "stb_default":  # Default style for static text box labels
        text.SetForegroundColour(COLOUR_BUTTON_TEXT_ACTIVE)
        fnt.SetPointSize(APP_FS + 2)
        text.SetOwnFont(fnt)
    elif style == "details_label":  # A style for the venue details - labels
        text.SetForegroundColour(COLOUR_TEXT_LABELS)
        text.SetBackgroundColour(COLOUR_PANEL_BG)
        fnt.SetPointSize(APP_FS + 2)
        text.SetOwnFont(fnt)
    elif style == "details_venue_name":  # A style for the venue details - venue name
        text.SetForegroundColour(COLOUR_TEXT_DATA)
        text.SetBackgroundColour(COLOUR_PANEL_BG)
        fnt.SetFaceName("Segoe UI Semibold")
        fnt.SetPointSize(APP_FS + 3)
        text.SetOwnFont(fnt)
    elif style == "details_text":  # A style for the venue details - data
        text.SetForegroundColour(COLOUR_TEXT_DATA)
        text.SetBackgroundColour(COLOUR_PANEL_BG)
        text.SetMinSize((-1, 21))
        fnt.SetFaceName("Segoe UI Semibold")
        fnt.SetPointSize(APP_FS + 2)
        text.SetOwnFont(fnt)


"""
### GUI - Dialogue & Message boxes 
"""


def on_about(_):
    about_info = AboutDialogInfo()
    about_info.SetName(APP_NAME)
    about_info.SetVersion(BUILD_VER)
    about_info.SetDescription(
        """\n          A Really Self Evident Computer and Network Device Interface
        \n       [ Consolidating front-end for the monitoring and control of remote        
             Audio-Visual devices installed within the UWA campus network ]\n\n
        Connections exist for the following applications:\n        
                AirTable
                Asana
                WebSiS
                Callista
                DameWare(10)64bit
                telnetUltra
                UltraVNC
                Wireless Workbench 6
                WMI Ping
        """)
    about_info.SetCopyright("(C) 2019  Peter C Todd")
    about_info.SetWebSite("http://www.vitamin-ha.com/wp-content/uploads/2012/11/meanwhile-in-scotland.jpg",
                          "UWA Audio-Visual")
    wx.adv.AboutBox(about_info)


def msg_warn(parent, message, caption="Warning!"):
    dlg = wx.MessageDialog(parent, message, caption, wx.OK | wx.ICON_WARNING)
    dlg.ShowModal()
    dlg.Destroy()


"""
### Launch external apps 
"""


def _launch_main_browser(progstring, ipstring, new_window=False):
    try:
        if new_window:
            subprocess.Popen([progstring, "--window-size=1024,768", "--new-window", ipstring])
            # opens chrome with new window at address passed, if Chrome is already open it ignores sizing flags :(
        else:
            subprocess.Popen([progstring, "--window-size=1024,768", ipstring])  # new tab
    except OSError as e:
        print("Browser failed to run:", e)
        msg_warn(MainFrame, f"Browser failed to run:\n{progstring}\n\nCheck: View -> Settings\n\n{e}")


def _launch_alt_browser(progstring, ipstring):
    try:
        subprocess.Popen([progstring, ipstring])
        # opens ie (or firefox) with new window at address passed
    except OSError as e:
        print("Alternative browser failed to run:", e)
        msg_warn(MainFrame, f"Alternative browser failed to run:\n{progstring}\n\nCheck: View -> Settings\n\n{e}")


""" chrome switches: https://www.ghacks.net/2013/10/06/list-useful-google-chrome-command-line-switches/"""


def bg_refresh_permitted(new_data=False):
    """
    Determines if there's a need to do a background (threaded) check of our data against AirTable data.

    If we've already fetched new data on loading OR the data in app was already checked today, we skip doing the refresh

    :param new_data: True means that a new JSON file has already been loaded into the app
    :return: boolean: True -> Permit background refresh; False -> don't permit background refresh
    """

    now = time.localtime()  # format is (tm_year,tm_mon,tm_mday,tm_hour,tm_min, tm_sec,tm_wday,tm_yday,tm_isdst)
    last = prefs_dict["last_data_refresh"]  # stored in the same format as above
    if not (now[2] == last[2]) or new_data:
        print(now[2], last[2], now[2] == last[2])
        print(bool(not new_data))
        return True

    return False


if __name__ == '__main__':
    app = wx.App(False)
    # a list of venue dictionaries, needed before drawing VenuesPanel
    venues_full, update_has_run, fail_msg = arsecandi.get_venue_list(DATA_DIR)

    if fail_msg:
        msg_warn(None, fail_msg)
        if not venues_full:
            msg_warn(None, "No local or remote data available\n\nNothing to load => Closing ArseCandi")
            print('No data: shutting down ArseCandi')
            quit()

    # If we've just loaded data from Airtable, we don't need to do another refresh in the background
    print(f'Background refresh will run?: {bg_refresh_permitted(update_has_run)}')

    # wx.lib.inspection.InspectionTool().Show()
    MainFrame(None).Show()
    app.MainLoop()
