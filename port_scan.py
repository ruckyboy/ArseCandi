import socket
import subprocess
import sys
from datetime import datetime

# Ask for input
# remoteServer = input("Enter a remote host to scan: ")
# remoteServer = "10.109.16.54"   # Sanders G06 ULXD4
remoteServer = "10.109.8.119"   # Park Ave LT ULXD4
# remoteServer = "10.109.16.105"   # Simmonds LT Panasonic projector - Port 1024 default
remoteServer = "10.109.16.107"   # Simmonds LT ULXD4
remoteServer = "10.0.0.1"   # local


remoteServerIP = socket.gethostbyname(remoteServer)

# Print a nice banner with information on which host we are about to scan
print("-" * 60)

print("Please wait, scanning remote host ", remoteServerIP)

print("-" * 60)


# Check what time the scan started
t1 = datetime.now()

wwb6_ports = [21, 23, 2202, 8023, 64000, 68, 5568, 8427]

try:
    for port in wwb6_ports:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(0.5)
        result = sock.connect_ex((remoteServerIP, port))
        if result == 0:
            print(f"Port {port}:    Open")
        else:
            print(f'Port {port}:    *')
        sock.close()

except KeyboardInterrupt:
    print("You pressed Ctrl+C")
    sys.exit()

except socket.gaierror:
    print('Hostname could not be resolved. Exiting')
    sys.exit()

except socket.error:
    print("Couldn't connect to server")
    sys.exit()

t2 = datetime.now()
total = t2 - t1
print('Scanning Completed in: ', total)
