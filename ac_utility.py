import hashlib
import shelve
import os
from pathlib import Path
from random import randrange
import time
from datetime import datetime
from telnetlib import Telnet
from telnetlib import socket
from wx import Display as Display

"""
#########################################################################################
   File related utilities
#########################################################################################
"""


def random_file(path=None, ext_list=None):
    """
    Returns a random file from the given directory path, matching the extension/s passed

    :param path: Path to the directory. Full or relative. Current directory if no path is passed
    :param ext_list: list of file extensions as strings, including dot eg['.jpg', '.bmp', '.png', '.gif']
    :return: path to a randomly selected file
             If no extension is given, returns any file found
             None if nothing matched
    """

    included_extensions = ext_list if ext_list else [""]
    file_names = [fn for fn in os.listdir(path) if any(fn.endswith(ext) for ext in included_extensions)]

    if len(file_names) > 0:
        return file_names[randrange(len(file_names))]
    else:
        return None


def get_file_timestamp(path):
    return datetime.fromtimestamp(path.stat().st_mtime).strftime('%d %b %Y %H:%M:%S')


def get_md5(file_path: Path):
    """
    Returns MD5 hash on given file, returns None if file does not exist or no MD5 hash generated

    :param file_path: Path of the file to be checked. Full or relative
    :return: (MD5 hashcode)
    """

    file_name = str(file_path)
    try:
        with open(file_name, "rb") as file_to_check:
            # read contents of the file as binary
            data = file_to_check.read()
            # pipe contents of the file through
            return hashlib.md5(data).hexdigest()
    except FileNotFoundError:
        print(f"{file_name}: file not found")
        return None


def replace_with_updated(f_target: Path, f_candidate: Path, f_backup: Path = None):
    """
    Replaces(overwrites) a file with another if MD5s are different, optionally backing up the original file

    Will create a new file if f_original does not exist
    The f_candidate file will be renamed (in effect it's 'deleted') not copied.

    :param f_target: Path of the file to be replaced. Full or relative
    :param f_candidate: Path of the possible replacement file. Full or relative
    :param f_backup: Path of the backup file. Full or relative
    :return: (Boolean, datetime -in seconds) True if the file is written/overwritten; the replacement file datetime
                                             False if files are equal; the original file datetime
                                             False if process failed; None (no file datetime to return)
    """

    def quit_on_fail(msg):
        print(msg)
        return False, None

    # Checking the newly created .tmp file against the current .json file to see if there is a difference
    # If there is a difference, assume that the .tmp file contains new information and needs to be saved
    # as the working .json file, the old .json is then renamed to .bak, ( for just in case)

    if not f_candidate.exists():  # Make sure the replacement file exists otherwise back out of changes
        quit_on_fail('Candidate file not found - quitting')

    elif f_target == f_candidate or f_target == f_backup or f_candidate == f_backup:
        quit_on_fail('File paths are not unique - quitting')

    else:
        # os.path.getmtime returns file modification time in seconds since epoch
        new_file_time = f_candidate.stat().st_mtime  # 'data/icandi.tmp'
        new_md5 = get_md5(f_candidate)

        if not f_target.exists():  # If no original file exists, just replace it and return
            f_candidate.replace(f_target)
            return True, new_file_time
        else:
            # Compare original file MD5 with temporary file MD5 and act on result
            # original_file_time = datetime.fromtimestamp(os.path.getmtime(f_target))
            original_file_time = f_target.stat().st_mtime
            orig_md5 = get_md5(f_target)

        if orig_md5 == new_md5:
            try:
                # If the .tmp file exists then delete it
                f_candidate.unlink()
                return False, original_file_time
            except FileNotFoundError:
                quit_on_fail(f"Could not find the temporary file '{f_candidate}'")

        else:
            print(f"MD5 differences found.\n New:\t {new_md5}\n Old:\t {orig_md5}")
            try:
                if f_backup:  # If there is already a .json file then rename it to .bak
                    # .replace overwrites destination file; or creates it if none exists
                    f_target.replace(f_backup)  # "data/icandi.bak"
                    f_candidate.replace(f_target)  # "data/icandi.json"  # Rename the .tmp to .json
                return True, new_file_time
            except (FileExistsError, FileNotFoundError):
                quit_on_fail("Failure updating files for some reason")


"""
#########################################################################################
   Preference Shelf related utilities
#########################################################################################
"""

DEFAULT_PREFS = {
    "bearer_key": "keyfppFBhdYli2nSr",
    "airtable_url": "https://api.airtable.com/v0/appXOyM6EA9QQpWU0/Venue?view=iCandi",
    "airtable_web": "https://airtable.com/tblFYadwHdtDdKnV1/viw0KhCtD6urafgST",
    "callista_root": "https://applicant.sims.uwa.edu.au/connect/webconnect?pagecd=UPTMTBL"
                     "&dataname=%7Cp_mode%7Cp_ret%7Cp_draft_ind%7Cp_uoos&datavalue=%7CVENUE%7CDTL%7CY%7C",
    # Settings window parameters
    "staff_id": "900xxxxx",
    "main_browser": "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
    "alt_browser": "C:\\Program Files\\internet explorer\\iexplore.exe",
    "dameware": "C:\\Program Files\\SolarWinds\\DameWare Mini Remote Control 10.0 x64\\DWRCC.exe",
    "shure": "C:\\Program Files\\shure\\wireless workbench 6\\Wireless Workbench 6.exe",
    "vnc": "C:\\Program Files\\uvnc bvba\\UltraVNC\\vncviewer.exe",
    "telnet": "C:\\Windows\\WinSxS\\"
              "amd64_microsoft-windows-telnet-client_31bf3856ad364e35_10.0.17134.1_none_9db21dbc8e34d070\\telnet.exe",
    "timetable_url": "http://timetable.applications.uwa.edu.au/venue.html?",
    "res_booker_url": "https://resourcebooker.uwa.edu.au/#/app/booking-types",
    "echo_monitor_url": "echo360.org",
    "echo_captures_url": "https://echo360.org.au/admin/captures",
    "camera_refresh": 5000,
    "ping_timeout": 1000,
    "ping_batch_size": 100,
    # Main window parameters
    "ping_on_select": False,
    "devicelist_show_flagged": False,
    "last_data_refresh": time.localtime(),
    # App window sizing - restored when app starts
    "win_max": False,
    "win_size": (-1, -1),
    "win_pos": (-1, -1)
}


def preferences(location=Path.cwd(), action="", key=None, value=None):
    """
    Returns all key/value pairs of the preferences shelf; specify the location, otherwise working directory is assumed
    Takes optional action values:
           'default' generates a new data file with default values, replaces existing file if present;
           'update' updates the passed key value pair, both key and value must be passed otherwise update is ignored

    :param location: Directory of preferences data files: As pathlib.Path object
           If location isn't passed, working directory is assumed ( CWD )
           If directory or file doesn't exist, they will be created, with default values
    :param action: [str] optional
    :param key: [str] key name, for update only
    :param value: [str] key value, for update only
    :return: (dictionary) all key/value pairs from preference settings
    """

    # TODO validate user input from the settings page, min / max and default values where needed
    file_location = location / "preferences"

    if not location.exists():
        location.mkdir()
    if not file_location.with_suffix(".dat").exists() or not file_location.with_suffix(".dir").exists() or \
            action == "default":
        _set_default_preferences(file_location)

    with shelve.open(str(file_location)) as pref:  # shelve.open() defaults to flag='c'
        if action == "update" and key and value is not None:  # If no value is passed it will default to False
            pref[key] = value
        return dict(pref)

    # TODO Load defaults from file - make script to create file


def _set_default_preferences(file_location):
    """ * do not access externally *
        Creates a new preferences shelf with default values (from DEFAULT_PREFS);
        flag='n' -> always create new shelve object, replaces an existing shelve if present
    """

    with shelve.open(str(file_location), flag='n', writeback=True) as pref:
        for k, v in DEFAULT_PREFS.items():
            pref[k] = v


"""
#########################################################################################
   Network related utilities
#########################################################################################
"""


# TODO examine and workout watch-strings and responses, take into account DGX needs login


def reboot_via_telnet(ip="rainmaker.wunderground.com", user=None, password=None):
    """
    Function to reboot AMX devices over telnet

    :param ip: str: Host name or IP address
    :param user: str:   logon name
    :param password: str:   logon password
                            If name and password are passed, assumes logging into DGX
    :return: str:   Captured interaction with host
    """
    # \r = carriage return; \n = line feed; \r\n = carriage return line feed (CRLF)
    # 'Enter' requirements are dependant on the 'server'; AMX accepts \r

    # ip = "rainmaker.wunderground.com"        # accepts \n as 'Enter'  test public accessible telnet host

    ret_str = "#" * 50 + '\r\n\r\n'  # ret_str is built up of all responses and inputs during the session

    # todo test DGX reboot > live
    if user and password:
        print("Running DGX script")
        try:
            with Telnet(ip, timeout=3) as tn:
                response_str = tn.read_until(b"user:", 3).decode('ascii')
                ret_str += response_str + "\r\n"
                # print(ret_str)
                time.sleep(1)
                inp = "administrator"
                ret_str += f'\t->{inp} \r\n'
                tn.write(inp.encode('ascii') + b"\r")
                response_str = tn.read_until(b"password:", 3).decode('ascii')
                ret_str += response_str + "\r\n"
                # print(ret_str)
                time.sleep(1)
                inp = "password"
                ret_str += f'\t->{inp} \r\n'
                tn.write(inp.encode('ascii') + b"\r")
                response_str = tn.read_until(b">", 3).decode('ascii')
                ret_str += response_str + "\r\n"
                # print(ret_str)
                time.sleep(1)
                inp = "reboot"
                ret_str += f'\t->{inp} \r\n'
                tn.write(inp.encode('ascii') + b"\r")
                response_str = tn.read_until(b"system...", 3).decode('ascii')
                ret_str += response_str + "\r\n"
                # print(ret_str)
                time.sleep(1)
                tn.write(b"\r")
        except (TimeoutError, socket.timeout):
            # import sys        # These 3 lines are a good way to discover the exception/s raised
            # exc_info = sys.exc_info()
            # print(exc_info)
            print("Could not connect to host")
            ret_str += f"Could not connect to {ip} \r\n"

    else:
        try:
            with Telnet(ip, timeout=3) as tn:
                response_str = tn.read_until(b">", 3).decode('ascii')
                ret_str += response_str + "\r\n"
                # print(ret_str)
                time.sleep(1)
                inp = "reboot"
                ret_str += f'\t->{inp} \r\n'
                tn.write(inp.encode('ascii') + b"\r")
                response_str = tn.read_until(b">", 3).decode('ascii')
                ret_str += response_str + "\r\n"
                # print(ret_str)
                time.sleep(1)
                tn.write(b"\r")
        except (TimeoutError, socket.timeout):
            print("Could not connect to host")
            ret_str += f"Could not connect to {ip} \r\n"

    ret_str += "\r\n" + "#" * 50 + "\r\n"
    return ret_str


# TODO some code to plunder for threading the telnet session
"""
import threading
import sys
import os
import unidecode
import telnetlib
import time
import re
from time import sleep
outfile = open('zyxelmac.txt','w')
def open_telnet(ip):
        user = 'admin'
        password = '1234'
        sr_no = 0
        try:
            telnet = telnetlib.Telnet(ip, 23, 2)
            telnet.read_until('User name:', 3)
            telnet.write(user.encode('ascii') + '\r')
            telnet.read_until('Password:', 3)
            telnet.write(password.encode('ascii') + '\r')
            telnet.write('statistics mac 1~48' + '\r\r\r\r')
            telnet.read_until('>')
            telnet.write(' exit''\r')
            output = telnet.read_all()
            sleep(2)
            data = iter(output.split('\n'))
 
            try:
                        for line in data:
                                if "Port:" in line:
                                        port1 = line.split(':')
                                        port = str(port1[:5])
                                        port2 = port[10:13].strip()
                                        port3 = port2.replace('\\','')
                                        next(data)
                                        next(data)
                                        port_mac = next(data)[1:]
                                        outfile.write(ip+' '+port3+' '+port_mac)
                                        outfile.write('\n')
            except StopIteration:
                   pass
        except Exception as excp:
            print(excp)
def create_threads():
    threads = []
    with open('zyxel.txt','r') as ipfile:
        for sr_no, line in enumerate(ipfile, start=1):
            ip = line.strip()
            th = threading.Thread(target = open_telnet ,args = (ip,))
            th.start()
            threads.append(th)
            for thr in threads:
                thr.join()
 
if __name__ == "__main__":
        create_threads()
        print "Exiting the program"
        outfile.close()
        
# https://python-forum.io/Thread-Multithread-telnet-not-working-Parallel

"""

"""
#########################################################################################
   Display related utilities
#########################################################################################
"""


def get_display_info():
    for i in range(Display.GetCount()):
        display = Display(i)
        print(display.GetName())
        print(display.GetGeometry())
    pass


if __name__ == '__main__':
    a = Path("a:\\text.txt")
    b = Path("c:\\text.txt")
    c = Path("c:\\text.txt")
    replace_with_updated(a, b, c)
    print(a)
    print(b)
    print(c)


"""
#########################################################################################
   Bitwise checking utilities
#########################################################################################
"""


def check_bit_set(value: int, bit: int):
    """
    Simple function to determine if a particular bit is set
    eg (12 - binary 1100) then positions 3 and 4 are set
    :param value:   Number to be tested
    :param bit:     Position to check; >0 (right to left)
    :return: Bool:  True if bit is set
    """
    if value & (1 << (bit - 1)):
        return True
