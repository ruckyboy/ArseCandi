import json
from collections import Counter
import ac_json
from ac_constants import *


def get_venue_list(location: Path, force_build=False):
    """

    :param location: Path: location of the main icandi.json file
    :param force_build: Boolean: True -> will dump current .json file and rebuild a new one from AirTable
    :return: tuple: (venue_list: list: a list of venue dictionaries,
                     new_data: boolean: True if new icandi JSON file created, False if using current iCAndi JSON file)
                     fail_msg: str: If present, passes through fail message from build_icandi_json; else None
    """
    fail_msg = None
    new_data = False
    # If ArseCandi's underlying json file is missing or we've forced a rebuild > then rebuild it from AirTable
    if not (DATA_DIR / "icandi.json").exists() or force_build:
        if force_build:
            msg = "Checking for updated data...\n(Fetching from AirTable)"
        else:
            msg = " No local json file found.\nFetching current data from AirTable..."
        print(msg)
        new_data, fail_msg = ac_json.build_icandi_json()

    if fail_msg:
        return [], new_data, fail_msg

    ac_json_file = location / "icandi.json"

    with ac_json_file.open('r') as file:
        venue_list = json.load(file)

    return venue_list, new_data, fail_msg


def get_venue_stats(venues_list):
    """
    A simple helper function to construct a dictionary of stats from the main venues list

    :param venues_list: list of venue dictionaries
    :return: dict
    """
    stats_dict = {}
    ctf = Counter(item['ctf'] for item in venues_list)
    stats_dict['ctf_y'] = ctf['Yes']
    stats_dict['ctf_n'] = ctf['No']
    stats_dict['ctf_tot'] = sum(ctf.values())

    pcs = Counter(item['ctf'] for item in venues_list if item['pc'])
    stats_dict['ctf_y_pc'] = pcs['Yes']
    stats_dict['ctf_n_pc'] = pcs['No']
    stats_dict['ctf_tot_pc'] = sum(pcs.values())

    echo = Counter(item['ctf'] for item in venues_list if item['echo360'])
    stats_dict['ctf_y_echo'] = echo['Yes']
    stats_dict['ctf_n_echo'] = echo['No']
    stats_dict['ctf_tot_echo'] = sum(echo.values())

    cam = Counter(item['ctf'] for item in venues_list if item['webcam'])
    stats_dict['ctf_y_cam'] = cam['Yes']
    stats_dict['ctf_n_cam'] = cam['No']
    stats_dict['ctf_tot_cam'] = sum(cam.values())

    camtype = Counter(item['webcamtype'] for item in venues_list if item['webcam'])
    stats_dict['camtype_vb10'] = camtype['VB10']
    stats_dict['camtype_vb41'] = camtype['VB41']
    stats_dict['camtype_vb50'] = camtype['VB50']
    stats_dict['camtype_vb60'] = camtype['VB60']
    stats_dict['camtype_sony'] = camtype['SonyCam']
    stats_dict['camtype_tot'] = sum(camtype.values())

    alloc_tot = 0
    active_alloc_tot = 0
    for item in venues_list:
        for ip in item['networkdevice']:
            if '[' not in ip[0]:    # removes PC, Echo and cameras from the ip address list
                alloc_tot += 1
                if '*' not in ip[0]:    # further removes non-active ip addresses
                    active_alloc_tot += 1

    stats_dict['ip_alloc_tot'] = alloc_tot
    stats_dict['ip_active_alloc_tot'] = active_alloc_tot

    return stats_dict


if __name__ == '__main__':
    from pprint import pprint

    def test_get_venue_list():
        venuelist, is_new_data, msg = get_venue_list(DATA_DIR)
        print()

        # Print out entire list of venue dictionaries
        itemcount = 0
        for i in venuelist:
            itemcount += 1
            for k, v in i.items():
                if k == "notes":
                    v = repr(v)
                    # this handles the \r print output problem in the notes field, just for this test print only
                print(k + " = " + str(v))
            print("---------------------------" + str(itemcount))
        print()

        print(f'Database updated by get_venue_list: {is_new_data}')
        print(f'{len(venuelist)} records found\nPassed Message: {msg}')

    def test_get_stats_dict():
        venuelist, is_new_data, msg = get_venue_list(DATA_DIR)
        stats_dict = get_venue_stats(venuelist)
        pprint(stats_dict)

    test_get_stats_dict()