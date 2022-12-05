import network
import usocket
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


def reconnect_wifi():
    if wlan.status() != network.STAT_GOT_IP:
        wlan.disconnect()
    while wlan.status() != network.STAT_GOT_IP:
        if wlan.status() == network.STAT_WRONG_PASSWORD:
            raise RuntimeError('wrong WiFi password')
            sys.exit()
        elif wlan.status() != network.STAT_CONNECTING:
            wlan.connect(secrets.wifi_ssid, secrets.wifi_password)

        print('waiting for connection...')
        time.sleep(0.5)

    print('connected')
    ip_address = wlan.ifconfig()[0]
    print(f'ip = {ip_address}')

    request = urequests.get(secrets.ddns_url + f'&myip={ip_address}')
    print(request.content)
    request.close()


led = machine.Pin('LED', machine.Pin.OUT)

patterns = {
    "uihsaduha": {
        "active": True,
        "name": "Static green/red",
        "author": "Joel",
        "date": "Today",
        "script": "if led % 2 == 0:\n    return 255, 0, 0\nelse:\n    return 0, 255, 0"
    },
    "dsafqwwea":{
        "active": False,
        "name": "Static white",
        "author": "Joel",
        "date": "Today",
        "script": "return 255, 255, 255"
    }
}

html = html.generate_html(json.dumps(json.dumps(patterns)))

reconnect_wifi()


async def serve_client(reader, writer):
    print("Client connected")
    request_line = await reader.readline()
    print("Request:", request_line)

    while await reader.readline() != b'\r\n':
        pass

    writer.write('HTTP/1.0 200 OK\r\nContent-type: text/html\r\n\r\n')
    writer.write(html)
    await writer.drain()
    await writer.wait_closed()
    print("Client disconnected")


async def main():
    print('Setting up webserver...')
    uasyncio.get_event_loop().create_task(uasyncio.start_server(serve_client, "0.0.0.0", 80))
    while True:
        led.on()
        await uasyncio.sleep(0.25)
        led.off()
        await uasyncio.sleep(5)

try:
    uasyncio.run(main())
finally:
    uasyncio.new_event_loop()
