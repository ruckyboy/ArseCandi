import json
import requests
import time
from urllib import parse
from datetime import datetime
import ac_utility
from ac_constants import *

"""
    # The json from Airtable is processed first in build_icandi_json, parsed then saved locally to icandi.json
    # icandi.json is then loaded into get_venue_list for processing.
    # Benefits: local data is persistent and doesn't rely on internet connection
    # Airtable data can be parsed, filtered and then well formed before being written local
"""


def load_sims(url, options):
    """ sims returns a jquery? object of all room booking items (dictionaries) """

    try:
        pulljson = requests.get(url + options)
        status = pulljson.status_code
    except (requests.Timeout, requests.ConnectionError, KeyError, Exception) as e:
        print(f'Exception raised: {e}')
        pulljson = {}
        status = 408
    return pulljson, status


def build_sims_json(sims_id):
    # todo set this as a pref key and with advanced settings option
    sims_root = "https://applicant.sims.uwa.edu.au/connect/webconnect?" \
                "pagecd=UPTMTBL&dataname=%7Cp_mode%7Cp_ret%7Cp_draft_ind%7Cp_uoos&datavalue=%7CVENUE%7CDTL%7CY%7C"
    # sims_query = parse.quote_plus('ARTS: [  G59] Fox Lecture Ha', safe='/&=')
    sims_query = parse.quote_plus(sims_id, safe='/&=')

    req, json_request_status = load_sims(sims_root, sims_query)
    if json_request_status == requests.codes.ok:

        today_iso = datetime.now().date()
        current_year, current_week, _ = today_iso.isocalendar()
        # current_week = 4

        bookings_list = []
        cleaned_response = (req.text[1:-11])  # remove cruft from top and tail of response
        loaded = json.loads(cleaned_response)
        # the return from the query is a mish mash of stuff, not json, no consistency in formatting, etc  X:(
        for booking in loaded[1:]:  # dump the first record - just structure info
            bookingdetail = {}
            bookingdetail["title"] = booking.get("actLongFrm", "MISSING").replace("_", " ")
            bookingdetail["day"] = booking.get("day", "MISSING")
            bookingdetail["duration"] = booking.get("sttoend", "MISSING")
            # bookingdetail["weeknos"] = booking.get("wknos", "MISSING")

            weeks = booking.get("wknos", "MISSING").split(',')
            while "" in weeks:
                weeks.remove("")
            bookingdetail["weeks"] = list(map(int, weeks))

            b_start, b_end = bookingdetail["duration"].split(" - ")   # split "duration" into start and end time strings
            g_start = int(b_start.split(":")[0])    # convert the start string into int of hour value
            bookingdetail["g_start"] = g_start if g_start > 7 else 7  # grid start time is no less than 7
            g_end = int(b_end.split(":")[0])    # convert the start string into int of hour value
            if g_end == 0:
                g_end = 24   # make booking times finish at 24:00 hours (not 00:00)
            bookingdetail["g_span"] = g_end - g_start

            if current_week in bookingdetail["weeks"]:
                bookings_list.append(bookingdetail)

        # todo we can not bother writing to disk after testing
        temp_json_file = DATA_DIR / "sims.json"
        with temp_json_file.open("w") as file:
            json.dump(bookings_list, file, indent=2)

        return bookings_list

    else:
        print(f'Failed to connect to sims\n\n({json_request_status})')
        print(ERROR_CODES.get(str(json_request_status), 'Error code not found'))


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
        print(f'Exception raised: {e}')
        pulljson = {}
        status = 408
    return pulljson, status


def build_icandi_json():
    # venue_records = None
    # venue_pages = None
    morepages = True
    offset = ""
    json_request_status = 0
    venue_list = []
    has_new_data = False
    fail_msg = None

    tmp_prefs = ac_utility.preferences(DATA_DIR)

    bearer_key = tmp_prefs["bearer_key"]
    # bearer_key = "BAD_KEY_FOR_TESTING"
    # bearer_key = "keyfppFBhdYli2nSr"
    # # Do Not use the url below - to get json from old iturd run icandi_json_iTurd.py
    # # url = "https://api.airtable.com/v0/appfybfS11FLtnOH8/Venue?view=XojoView"  # also from preferences - iTURD - old
    # url = "https://api.airtable.com/v0/appXOyM6EA9QQpWU0/Venue?view=iCandi"  # also from preferences - iTARD - new
    url = tmp_prefs["airtable_url"]
    options = ""
    # options = "&maxRecords=11&filterByFormula=(Group='Business School')"  # just for testing

    del tmp_prefs

    while morepages:

        req, json_request_status = load_airtable(bearer_key, url, options, offset)
        if json_request_status == requests.codes.ok:

            if "offset" in json.loads(req.content):  # offset is the second outermost key in the json dictionary
                offset = json.loads(req.content).get("offset")
            else:
                offset = ""

            venue_records = json.loads(req.content)["records"]
            # venue_records is a list of venue dictionaries {id:text, fields{dictionary}, createdTime:text}

            # Iterate through dictionary, extract only fields for use with ArseCandi
            for index, venue_record in enumerate(venue_records):
                venue = {"id": venue_record.get("id")}

                # print(venue_record)
                for venuekey in venue_record:
                    # Remove unused fields and rename used fields as needed
                    if "fields" in venuekey:
                        # Remember: AirTable returns no key if bool is False, we have to force a False value on booleans
                        # <Returned records do not include any fields with "empty" values, e.g. "", [], or false'>
                        fields = venue_records[index][venuekey]

                        venue["name"] = fields.get("Venue Name", "MISSING")
                        venue["code"] = fields.get("Room code", "MISSING")
                        venue["building"] = fields.get("_Building", "Unknown")
                        venue["bookingid"] = fields.get("Booking ID", "")   # Callista code
                        venue["aka"] = fields.get("AKA", "")
                        venue["capacity"] = int(fields.get("Capacity", 0))
                        venue["group"] = fields.get("Group", "Unknown")
                        venue["phone"] = str(fields.get("Phone", "Unknown"))
                        venue["ctf"] = "Yes" if fields.get("CTF") else "No"  # AirTable stored as boolean
                        venue["cardax"] = "Yes" if fields.get("Cardax") else "No"  # AirTable stored as boolean
                        venue["notes"] = fields.get("_Notes", "")
                        venue["pc"] = fields.get("_PC", "")
                        venue["webcam"] = fields.get("_WebCam", "")
                        venue["webcamtype"] = fields.get("_WebCamType", "")
                        venue["echo360"] = fields.get("_Echo360", "")
                        venue["websis"] = fields.get("Venue WebSIS Link", "")
                        venue["projection"] = fields.get("Projection", "")
                        venue["projector"] = fields.get("Projector", "")
                        venue["asana"] = fields.get("Asana tag", "")
                        venue["sdc"] = fields.get("_SDC_String", "")

                        # Construct a new key ["Devices ip"] by iterating through ["_Device Data"] - a list of
                        # semicolon separated device strings - "device name; ip; extension" and splitting into list
                        devicedata = fields.pop("_Device Data", None)  #
                        devicelist = []

                        if devicedata:
                            for d in devicedata:
                                devicelist.append(d.split('; '))

                        # add, pc, web cam and echo360 to the device/ip collection
                        pc = fields.get("_PC", "")
                        webcam = fields.get("_WebCam", "")
                        echo360 = fields.get("_Echo360", "")

                        # TODO make allowances for more than one webcam and pc per venue - requires Airtable adjustment

                        if webcam:
                            devicelist.append(("[WebCam]", webcam, "0"))
                        if echo360:
                            devicelist.append(("[Echo 360]", echo360, "0"))
                        if pc:
                            for item in pc.split(', '):
                                devicelist.append(("[Lectern PC]", item, "0"))

                        venue["networkdevice"] = devicelist

                venue_list.append(venue)

            if not offset:  # if offset has no value
                morepages = False
            print("Pages retrieved from Airtable; Offset = " + offset)

        else:
            print(f'Failed to connect to Airtable\n\n({json_request_status})')
            print(ERROR_CODES.get(str(json_request_status), 'Error code not found'))
            break

    ###################################
    # Write to new json file icandi.json - if needed

    if json_request_status == requests.codes.ok:
        temp_json_file = DATA_DIR / "icandi.tmp"
        # with open(temp_json_file, "w") as file:   # Raises a Pycharm warning -> open() expects a str not a Path object
        # writing in the style below circumvents raising a warning
        with temp_json_file.open("w") as file:
            json.dump(venue_list, file, indent=2)

        update_success, file_datetime = ac_utility.replace_with_updated(DATA_DIR / "icandi.json",
                                                                        DATA_DIR / "icandi.tmp",
                                                                        DATA_DIR / "icandi.bak")

        if file_datetime:
            date_response = datetime.fromtimestamp(file_datetime).strftime('%d %b %Y %H:%M:%S')
            if update_success:
                has_new_data = True
                print(f"Database updated: {date_response}")
            else:
                print(f"Database is up to date. Last modified: {date_response}")
        else:
            print("Unable to update database.")
            fail_msg = "Unable to update database.\nTry manual update"
            # Manual update could require deleting all icandi.* json files from data directory and restarting iCandi
    else:
        print("Problems with Airtable prevented any updating")
        http_err_msg = ERROR_CODES.get(str(json_request_status), 'Check AirTable API codes')
        fail_msg = f'Failed to connect to Airtable\n\n{json_request_status}: {http_err_msg}'

    ac_utility.preferences(DATA_DIR, "update", "last_data_refresh", time.localtime())
    return has_new_data, fail_msg


if __name__ == '__main__':
    # is_rebuilt, msg = build_icandi_json()
    # print(f'Database updated by build_icandi_json: {is_rebuilt}\nPassed Message: {msg}')

    build_sims_json()

    pass
