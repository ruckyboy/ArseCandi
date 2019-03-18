import requests
import json
import time
from datetime import datetime
from pathlib import Path
import wx
import utility

CWD = Path.cwd()
DATA_DIR = CWD / "data"  # directory location for the json files

# TODO run this as main, to look for differences between 1/3/19 .json data and add differences into iTard on Airtable


def load_airtable(bearer_key=None, url=None, options=None, offset=""):
    """ AirTable returns a json object of up to 100 records
        if there are more records, AirTable passes an offset attribute
        this offset can be used as a parameter in the query string to get the next 100 records
        once there are less than 100 records returned, the offset attribute is no longer passed"""

    header = {'authorization': 'Bearer ' + bearer_key}
    timeout = 8  # in seconds
    try:
        pulljson = requests.get(url + options + "&offset=" + offset, headers=header, timeout=timeout)
        status = pulljson.status_code
    except (requests.Timeout, requests.ConnectionError, KeyError, Exception) as e:
        print(e)
        pulljson = {}
        status = 408
    return pulljson, status


def build_icandi_json():
    # venue_records = None
    # venue_pages = None
    morepages = True
    offset = ""
    json_request_status = 0
    icandi_container = {"records": []}

    bearer_key = "keyfppFBhdYli2nSr"
    url = "https://api.airtable.com/v0/appfybfS11FLtnOH8/Venue?view=XojoView"  # also from preferences - iTURD - old
    # url = "https://api.airtable.com/v0/appXOyM6EA9QQpWU0/Venue?view=iCandi"  # also from preferences - iTARD - new
    options = ""
    # options = "&maxRecords=11&filterByFormula=(Group='Business School')"  # just for testing
    # options = "&maxRecords=11&filterByFormula=(Group='Arts')"  # just for testing
    # options = "&maxRecords=11&filterByFormula=(Group='Physics')"  # just for testing

    while morepages:

        req, json_request_status = load_airtable(bearer_key, url, options, offset)
        if json_request_status == requests.codes.ok:

            if "offset" in json.loads(req.content):  # offset is the second outermost key in the json dictionary
                offset = json.loads(req.content).get("offset")
            else:
                offset = ""

            venue_records = json.loads(req.content)["records"]
            # venue_records is a list of venue dictionaries {id:text, fields{dictionary}, createdTime:text}

            #######################################
            # Iterate through python dictionary, pruning and simplifying for use with iCandi

            for index, venue_record in enumerate(venue_records):
                # print(venue_record)
                for venuekey in venue_record:
                    # Remove unused fields and rename used fields as needed
                    if "fields" in venuekey:
                        fields = venue_records[index][venuekey]
                        fields.pop("Building", None)
                        fields["Building"] = fields.pop("_Building", None)
                        fields.pop("_SortPriority", None)
                        fields.pop("PC", None)
                        fields["PC"] = fields.pop("_PC", None)
                        fields.pop("Radio Mic Frequency", None)
                        fields["Radio Mic Frequency"] = fields.pop("_Radio Mic Frequency", None)
                        fields.pop("Web Cameras", None)
                        fields["WebCam"] = fields.pop("_WebCam", None)
                        fields.pop("WebCamType", None)
                        fields["WebCamType"] = fields.pop("_WebCamType", None)
                        fields.pop("_Echo360Address", None)
                        fields.pop("Echo 360", None)
                        fields["Echo 360"] = fields.pop("_Echo360", None)
                        fields.pop("IP Allocations", None)
                        fields.pop("Building WebSIS Link", None)

                        # AirTable returns empty value if boolean is False, we have to force a False value on booleans
                        fields["CTF"] = fields.get("CTF", False)
                        fields["Cardax"] = fields.get("Cardax", False)

                        # Construct a new key ["Devices ip"] by iterating through ["Device Type"]&["Device Address"]
                        # keys then matching them up to form Key Value pairs, AirTable supplies both in synced order
                        # also add, pc, web cam and echo360 to the device/ip collection

                        pc = fields.get("PC")
                        webcam = fields.get("WebCam")
                        echo360 = fields.get("Echo 360")

                        # We don't need _Device Type or _Device Address after this so pop them out
                        devicetype = fields.pop("_Device Type", None)
                        deviceaddress = fields.pop("_Device Address", None)
                        devicelist = []

                        if devicetype and deviceaddress:
                            if len(devicetype) == len(deviceaddress):
                                devicelist = list(zip(devicetype, deviceaddress))
                            else:
                                print("Mismatch in device types / device ip count")
                        if webcam:
                            devicelist.append(("[WebCam]", webcam))
                        if echo360:
                            devicelist.append(("[Echo 360]", echo360))
                        if pc:
                            for item in pc.split(', '):
                                devicelist.append(("[Lectern PC]", item))
                        fields["Devices ip"] = devicelist

                icandi_container["records"].append(venue_record)

            if not offset:  # if offset has no value
                morepages = False
            print("Pages retrieved from Airtable; Offset = " + offset)

        else:
            print("Failed to connect to Airtable :(")
            break

    ###################################
    # Write to new json file icandi.json - if needed

    if json_request_status == requests.codes.ok:
        temp_json_file = DATA_DIR / "icandi.tmp"
        # with open(temp_json_file, "w") as file:   # Raises a Pycharm warning -> open() expects a str not a Path object
        # writing in the style below circumvents raising a warning
        with temp_json_file.open("w") as file:
            json.dump(icandi_container, file, indent=2)

        update_success, file_datetime = utility.replace_with_updated(DATA_DIR / "icandi.json",
                                                                     DATA_DIR / "icandi.tmp",
                                                                     DATA_DIR / "icandi.bak")

        if file_datetime:
            date_response = datetime.fromtimestamp(file_datetime).strftime('%d %b %Y %H:%M:%S')
            if update_success:
                print(f"Database updated: {date_response}")
            else:
                print(f"Database is up to date. Last modified: {date_response}")
        else:
            print("Unable to update database. Try manual update")
    else:
        print("Problems with Airtable prevented any updating")

    utility.preferences(DATA_DIR, "update", "last_data_refresh", time.localtime())


def get_venue_list(location: Path, force_build=False):
    if not (DATA_DIR / "icandi.json").exists():
        msg = " iCandi: First time run.\n\nFetching data from AirTable..."
        # busy_dlg = wx.BusyInfo(msg)
        build_icandi_json()
        # del busy_dlg
    elif force_build:
        build_icandi_json()

    venue_list = []  # contains a list of venue dictionaries (pulled from json)
    venue = {}  # instantiate a new venue to add to venue_list
    icandi_json = location / "icandi.json"

    # The json from Airtable is processed first in jsonreadwrite.py, parsed then saved locally to icandi.json
    # icandi.json is then loaded into here for processing.
    # Benefits: local data is persistent and doesn't rely on internet connection
    # Airtable data can be parsed, filtered and then well formed before being written local

    with icandi_json.open('r') as file:
        venue_records = json.load(file)["records"]

    # venue_records is a list of venue dictionaries {id:text, fields{dictionary}, createdTime:text}

    current_venue = 0
    for venue_record in venue_records:
        # print(venue_record)
        venue["id"] = venue_record.get("id")
        for venuekey in venue_record:

            if "fields" in venuekey:
                fields = venue_records[current_venue][venuekey]
                for fieldkey in fields:
                    # if a key isn't found, .get returns a None, you can assign a different value if None
                    #  1 if a > b else -1 if a < b else 0  * example chained ternary
                    venue["name"] = fields.get("Venue Name", "MISSING")
                    venue["code"] = fields.get("Room code", "MISSING")
                    venue["building"] = fields.get("Building", "Unknown")
                    venue["bookingid"] = fields.get("Booking ID", "No Booking ID")
                    venue["aka"] = fields.get("AKA", "")
                    venue["capacity"] = str(fields.get("Capacity", "Not supplied"))
                    venue["group"] = fields.get("Group", "Unknown")
                    venue["phone"] = str(fields.get("Phone", "Unknown"))
                    venue["ctf"] = "Yes" if fields.get("CTF") else "No"
                    venue["cardax"] = "Yes" if fields.get("Cardax") else "No"
                    venue["notes"] = fields.get("Notes", "")
                    venue["pc"] = fields.get("PC", "")
                    venue["radmicfreq"] = fields.get("Radio Mic Frequency", "")
                    venue["webcam"] = fields.get("WebCam", "")
                    venue["webcamtype"] = fields.get("WebCamType", "")
                    venue["echo360"] = fields.get("Echo 360", "")
                    venue["websis"] = fields.get("Venue WebSIS Link", "")
                    venue["projection"] = fields.get("Projection", "")
                    venue["projector"] = fields.get("Projector", "")
                    venue["asana"] = fields.get("Asana tag", "")
                    venue["networkdevice"] = fields.get("Devices ip", "")

        current_venue += 1
        venue_list.append(venue)
        venue = {}
    print("*" * 40)

    # # Test print
    # itemcount = 0
    # for i in venue_list:
    #     itemcount += 1
    #     for k, v in i.items():
    #         if k == "notes":
    #             v = repr(v)
    #             # this handles the \r print output problem in the notes field, just for this test print only
    #         print(k + " = " + str(v))
    #     print("---------------------------" + str(itemcount))

    return venue_list


if __name__ == '__main__':
    build_icandi_json()
    get_venue_list(DATA_DIR)
