import network
import socket
import time
import json
import html
import secrets

from machine import Pin

led = Pin('LED', Pin.OUT)

wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect(secrets.wifi_ssid, secrets.wifi_password)

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

max_wait = 10
while max_wait > 0:
    if wlan.status() < 0 or wlan.status() >= 3:
        break
    max_wait -= 1
    print('waiting for connection...')
    time.sleep(1)

if wlan.status() != 3:
    raise RuntimeError('network connection failed')
else:
    print('connected')
    status = wlan.ifconfig()
    print( 'ip = ' + status[0] )

addr = socket.getaddrinfo('0.0.0.0', 80)[0][-1]

s = socket.socket()
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind(addr)
s.listen(1)

print('listening on', addr)

# Listen for connections
while True:
    try:
        cl, addr = s.accept()
        print('client connected from', addr)
        request = cl.recv(1024)
        print(request)

        cl.send('HTTP/1.0 200 OK\r\nContent-type: text/html\r\n\r\n')
        cl.sendall(html)
        cl.close()

    except OSError as e:
        cl.close()
        print('connection closed')