import asyncio
import win32com.client
import time

wmi = win32com.client.GetObject(r"winmgmts:\\.\root\cimv2")  # Windows wmi service

""" Ping StatusCode_ReturnValues
  0='Success'
11001='Buffer Too Small'
11002='Destination Net Unreachable'
11003='Destination Host Unreachable'
11004='Destination Protocol Unreachable'
11005='Destination Port Unreachable'
11006='No Resources'
11007='Bad Option'
11008='Hardware Error'
11009='Packet Too Big'
11010='Request Timed Out'
11011='Bad Request'
11012='Bad Route'
11013='TimeToLive Expired Transit'
11014='TimeToLive Expired Reassembly'
11015='Parameter Problem'
11016='Source Quench'
11017='Option Too Big'
11018='Bad Destination'
11032='Negotiating IPSEC'
11050='General Failure'
"""


async def _ping_coroutine(ip, timeout):
    response = None
    wmi_resp = wmi.ExecQuery(
        f"Select ResponseTime, StatusCode from Win32_PingStatus Where Address = '{ip}' and timeout = {timeout}")
    await asyncio.sleep(0)  # not documented, but special case .sleep(0) will yield control to the main loop
    # print(f"{ip} wmi finished")
    for item in wmi_resp:
        if item.StatusCode == 0:
            response = f"{item.ResponseTime}ms"
        elif item.StatusCode == 11002:
            response = "Network unreachable"
        elif item.StatusCode == 11003:
            response = "Host unreachable"
        elif item.StatusCode == 11005:
            response = "Port unreachable"
        elif item.StatusCode == 11010:
            response = "Timed Out"
        elif item.StatusCode is None:
            response = "Not Found"
        else:
            response = "Failed"

    return ip, response


async def _batch_it(host_list, batch_size=100, ping_timeout=4000):
    """
    Asynchronous ping using WMI service as the ping instigator, Windows only of course
    :param host_list: List of ip addresses or host names or machine id's
    :param batch_size: default 100; how many hosts to ping at one time
                        consider cpu and network load before going crazy
    :param ping_timeout: default 1000ms, there seems to be a practical lower limit ~ 300ms?
    :return: currently using a tuple with host name and status/response
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


def main_start(site_list, batch=100, timeout=4000):
    asyncio.set_event_loop(asyncio.new_event_loop())

    # because this will be called repeatedly, I create a new loop, the option is to not close the first loop?
    loop = asyncio.get_event_loop()
    # >> > import threading
    # >> > t = threading.Thread(target=loop_in_thread, args=(loop,))
    # >> > t.start()
    # print("loop starting")
    elapse = time.time()
    ping_result = loop.run_until_complete(_batch_it(site_list, batch, timeout))
    # loop.run_in_executor(None, _batch_it, (site_list,))
    # how many IPs to ping at one time - consider cpu/network load
    # print("loop finished")
    # print(loop.is_closed())
    loop.close()
    # print("loop closed")
    print(time.time() - elapse)
    # print(bob)
    return ping_result


async def _batch_it_generators(host_gen, host_gen_count, batch_size=100, ping_timeout=4000):
    """
    Asynchronous ping using WMI service as the ping instigator, Windows only of course
    :param host_gen: generator yielding ip addresses or host names or machine id's
    :param host_gen_count: number of addresses to get from the generator
    :param batch_size: default 100; how many hosts to ping at one time
                        consider cpu and network load before going crazy
    :param ping_timeout: default 1000ms, there seems to be a practical lower limit ~ 300ms?
    :return: currently using a tuple with host name and status/response
    """
    ping_results = []
    pages = (host_gen_count // batch_size) + 1
    part_page = host_gen_count % batch_size
    print(host_gen_count, batch_size, pages, part_page)

    for i in range(0, pages):
        tasks = []
        if i == pages - 1:
            batch_size = part_page
        for _ in range(batch_size):
            tasks.append(asyncio.ensure_future(_ping_coroutine(next(host_gen), timeout=ping_timeout)))

        # for host in host_list:
        # # for host in host_list[i * batch_size:(i + 1) * batch_size]:
        #     # doesn't seem to throw an error if range exceeds actual items
        #     tasks.append(asyncio.ensure_future(_ping_coroutine(host, timeout=ping_timeout)))

        await asyncio.gather(*tasks)
        for resp in tasks:
            # print(resp.result())
            ping_results.append(resp.result())
        # print(f'page {i} finished')
    return ping_results


def main_start_generators(site_gen, site_gen_count, batch=100, timeout=1000):
    asyncio.set_event_loop(asyncio.new_event_loop())

    # because this will be called repeatedly, I create a new loop, the option is to not close the first loop?
    loop = asyncio.get_event_loop()
    elapse = time.time()
    ping_result = loop.run_until_complete(_batch_it_generators(site_gen, site_gen_count, batch, timeout))
    loop.close()
    time_taken = time.time() - elapse

    return ping_result, time_taken


if __name__ == '__main__':
    import random
    from collections import Counter
    from faker import Faker
    from faker.providers import internet

    """
    Batch size effects time to process (smaller=longer time: 100 is low load, slow; 2000 is high load, fast)
    Timeout also effects time to process (smaller = faster, 300 is lowest practical, 1000 is safe, 4000 is default)
    """

    gen_size = random.randint(100, 100)

    # Generate using faker for public ip addresses: https://faker.readthedocs.io/en/stable/
    fake = Faker()
    fake.add_provider(internet)

    # create a little generator for a random batch of addresses (rather than a hard list)
    sites_gen = (fake.ipv4_public() for p in range(0, gen_size))

    # Generate from short list of addresses/urls/names...
    # gen_size = random.randint(10, 100)  # 2000 take about 3.5 seconds :):):):):):)
    # address_list = ["slither.io", "uwa.edu.au", "www.uwa.edu.au", "google.com", "its00364", "35.160.169.47"]
    #
    # sites_gen = (random.choice(address_list) for p in range(0, gen_size))

    results, duration = main_start_generators(sites_gen, gen_size, batch=100, timeout=1000)

    # for result in results:
    #     host, status = result
    #     print(f"Host: {host} -> {status}")

    counts = Counter(x[1] for x in results)
    print(counts.most_common(10))  # leave out parameter for counts of every value of x[1]
    print(f'{len(results)} of {gen_size} items returned in {duration} seconds')
