import asyncio
import win32com.client
import time
# import pythoncom    # Only needed if we are using wmi in a thread (not needed otherwise)


async def _ping_coroutine(ip, timeout):
    response = None

    # pythoncom.CoInitialize()    # wmi must be co-initialized to work in thread (ignore pyCharm reference warning)
    wmi = win32com.client.GetObject(r"winmgmts:\\.\root\cimv2")  # Windows wmi service

    wmi_resp = wmi.ExecQuery(
        f"Select ResponseTime, StatusCode from Win32_PingStatus Where Address = '{ip}' and timeout = {timeout}")
    await asyncio.sleep(0)  # not documented, but special case .sleep(0) will yield control to the parent loop
    # print(f"{ip} wmi finished")

    for item in wmi_resp:
        if item.StatusCode == 0:
            response = f"{item.ResponseTime}ms"
        elif isinstance(item.StatusCode, int):
            response = _lookup_response_str(item.StatusCode)
        elif item.StatusCode is None:
            response = "Not Found"  # assumes DNS has failed to resolve an address
        else:
            response = "Failed"

    # pythoncom.CoUninitialize()  # finished with this thread (ignore pyCharm reference warning)
    return ip, response


async def _batch_it(host_list, batch_size=100, ping_timeout=4000):
    """
    Asynchronous ping using WMI service as the ping instigator, Windows only of course
    :param host_list: List of ip addresses or host names or machine id's
    :param batch_size: default 100; how many hosts to ping at one time
                        consider cpu and network load before going crazy
    :param ping_timeout: default 1000ms, there seems to be a practical lower limit ~ 300ms?
    :return tuple: (process_time: float, (host_name: str, response: str))
    """
    ping_results = []
    pages = (len(host_list) // batch_size) + 1
    for i in range(0, pages):
        tasks = []

        for host in host_list[i * batch_size:(i + 1) * batch_size]:
            # doesn't seem to throw an error if range exceeds actual items
            tasks.append(asyncio.ensure_future(_ping_coroutine(host, timeout=ping_timeout)))

        await asyncio.gather(*tasks)
        for resp in tasks:
            # print(resp.result())
            ping_results.append(resp.result())
    return ping_results


def _lookup_response_str(status_code):
    """
    Simple function to return a response string for a Ping StatusCode

    :param status_code: int:
    :return: str: Response string
    """
    status_msg = {0: 'Success',
                  11001: 'Buffer Too Small',
                  11002: 'Dest Net Unreachable',
                  11003: 'Dest Host Unreachable',
                  11004: 'Dest Protocol Unreachable',
                  11005: 'Dest Port Unreachable',
                  11006: 'No Resources',
                  11007: 'Bad Option',
                  11008: 'Hardware Error',
                  11009: 'Packet Too Big',
                  11010: 'Timed Out',
                  11011: 'Bad Request',
                  11012: 'Bad Route',
                  11013: 'TTL Expired Transit',
                  11014: 'TTL Expired Reassembly',
                  11015: 'Parameter Problem',
                  11016: 'Source Quench',
                  11017: 'Option Too Big',
                  11018: 'Bad Destination',
                  11032: 'Negotiating IPSEC',
                  11050: 'General Failure'}

    return status_msg.get(status_code, 'Unknown StatusCode')


def start(site_list, batch=100, timeout=4000):
    asyncio.set_event_loop(asyncio.new_event_loop())

    # because this will be called repeatedly, I create a new loop, the option is to not close the first loop?
    loop = asyncio.get_event_loop()
    elapse = time.time()
    ping_result = loop.run_until_complete(_batch_it(site_list, batch, timeout))

    loop.close()
    process_time = time.time() - elapse
    return ping_result, process_time


if __name__ == '__main__':
    import random
    from collections import Counter

    # batch size effects time to process (smaller=longer time: 100 is low load, slow; 2000 is high load, fast)
    # timeout also effects time to process (smaller = faster, 300 is lowest practical, 1000 is safe, 4000 is default)
    # Currently 2000 sites @ batch=2000, timeout=1000 takes about 3.5 seconds! :)

    list_size = random.randint(10, 10)
    address_list = ["slither.io", "uwa.edu.au", "www.uwa.edu.au", "google.com", "its00364", "35.160.169.47"]

    # create a list for a random batch of addresses
    sites_list = [random.choice(address_list) for p in range(0, list_size)]

    results, elapsed_time = start(sites_list, batch=2000, timeout=1000)

    # for result in results:
    #     host, status = result
    #     print(f"Host: {host} -> {status}")

    counts = Counter(x[1] for x in results)
    print(counts.most_common(10))  # for counts of every value of x[1], use empty parameter .most_common()
    print(f'{len(results)} of {list_size} addresses returned in {elapsed_time} seconds')
