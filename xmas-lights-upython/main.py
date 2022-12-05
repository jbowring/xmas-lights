import random
import network
import urequests
import time
import json
import html
import secrets
import sys
import machine
import uasyncio


wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.config(pm=0xa11140)

ip_address = ''


def reconnect_wifi():
    global ip_address

    if wlan.status() != network.STAT_GOT_IP:
        wlan.disconnect()
    while wlan.status() != network.STAT_GOT_IP:
        if wlan.status() == network.STAT_WRONG_PASSWORD:
            raise RuntimeError('wrong WiFi password')
        elif wlan.status() != network.STAT_CONNECTING:
            wlan.connect(secrets.wifi_ssid, secrets.wifi_password)

        print('waiting for connection...')
        time.sleep(0.5)

    print('connected')
    new_ip_address = wlan.ifconfig()[0]
    print(f'ip = {new_ip_address}')

    if ip_address != new_ip_address:
        ip_address = new_ip_address
        # TODO make async
        request = urequests.get(secrets.ddns_url + f'&myip={ip_address}')
        print(request.content)
        request.close()


led = machine.Pin('LED', machine.Pin.OUT)

patterns = {}

try:
    with open('patterns.json') as file:
        patterns = json.loads(file.read())
except (OSError, ValueError):
    pass

reconnect_wifi()


async def serve_client(reader, writer):
    request = b''
    while recv := await reader.read(1024):
        request += recv

        if len(recv) < 1024:
            break

    request = request.decode("utf8")
    print("Request:", request.split('\r\n')[0])

    if request.startswith('POST'):
        try:
            post_data = json.loads(request.split('\r\n\r\n')[1])
        except (IndexError, ValueError):
            pass
        else:
            if 'id' in post_data:
                pattern_id = post_data['id']
            else:
                pattern_id = str(random.getrandbits(32))

            keys = {
                'active': bool,
                'name': str,
                'author': str,
                'script': str,
            }

            # allow partial update if pattern_id already exists
            if pattern_id in patterns or all(key in post_data and isinstance(post_data[key], key_type) for key, key_type in keys.items()):
                if pattern_id not in patterns:
                    patterns[pattern_id] = {}
                for key, key_type in keys.items():
                    if key in post_data and isinstance(post_data[key], key_type):
                        if key == 'active' and post_data[key] is True:
                            for pattern in patterns.values():
                                pattern['active'] = False
                        patterns[pattern_id][key] = post_data[key]

                with open('patterns.json', 'w') as file:
                    file.write(json.dumps(patterns))

    writer.write('HTTP/1.0 200 OK\r\nContent-type: text/html\r\n\r\n')
    writer.write(html.generate_html(json.dumps(json.dumps(patterns))))
    await writer.drain()
    await writer.wait_closed()


async def main():
    print('Setting up webserver...')
    await uasyncio.get_event_loop().create_task(uasyncio.start_server(serve_client, "0.0.0.0", 80))
    while True:
        led.on()
        await uasyncio.sleep(0.25)
        led.off()
        await uasyncio.sleep(5)

try:
    uasyncio.run(main())
finally:
    uasyncio.new_event_loop()
