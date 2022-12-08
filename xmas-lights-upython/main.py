import math
import random
import network
import urequests
import time
import json
import html
import secrets
import neopixel
import machine
import usocket as socket
import sys
import io
import _thread
import gc

max_leds = 40
# led_strip = neopixel.NeoPixel(max_leds, 0, 22, 'GRB')  # TODO

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
        try:
            request = urequests.get(secrets.ddns_url + f'&myip={ip_address}')
            print(request.text)
            request.close()
        except Exception as exception:
            print(repr(exception))


reset = True
led = machine.Pin('LED')

patterns = {}

try:
    with open('patterns.json') as file:
        patterns = json.loads(file.read())
except (OSError, ValueError):
    pass

reconnect_wifi()


class HttpRequest:
    def __init__(self, request: bytes):
        self.request_text = request.decode("utf8")
        request_head_body = self.request_text.split('\r\n\r\n', 1)
        request_header_lines = request_head_body[0].split('\r\n')
        self.request_line = request_header_lines[0]

        try:
            self.headers = dict(split.split(': ', 1) for split in request_header_lines[1:-1])
        except (IndexError, TypeError):
            self.headers = {}

        try:
            self.body = request_head_body[1]
        except IndexError:
            self.body = ''


def led_thread():
    global reset
    global patterns
    current_pattern = None
    script = None
    global_scope = None
    local_scope = None
    time_seconds = 0
    timestep = 0.1
    timestep_us = int(timestep * 1e6)
    last_ticks_us = None

    while True:
        if reset:
            reset = False
            time_seconds = 0
            current_pattern = None
            script = None
            for pattern in patterns.values():
                if pattern['active']:
                    current_pattern = pattern
                    current_pattern['error'] = None
                    script = compile(current_pattern['script'], current_pattern['name'], 'exec')
                    global_scope = {
                        'math': math,
                        'random': random,
                        '__builtins__': {
                            'abs': abs,
                            'all': all,
                            'any': any,
                            'bin': bin,
                            'bool': bool,
                            'bytearray': bytearray,
                            'bytes': bytes,
                            'callable': callable,
                            'chr': chr,
                            'complex': complex,
                            'delattr': delattr,
                            'dict': dict,
                            'dir': dir,
                            'divmod': divmod,
                            'enumerate': enumerate,
                            'filter': filter,
                            'float': float,
                            'frozenset': frozenset,
                            'getattr': getattr,
                            'globals': globals,
                            'hasattr': hasattr,
                            'hash': hash,
                            'help': help,
                            'hex': hex,
                            'id': id,
                            'int': int,
                            'isinstance': isinstance,
                            'issubclass': issubclass,
                            'iter': iter,
                            'len': len,
                            'list': list,
                            'locals': locals,
                            'map': map,
                            'max': max,
                            'memoryview': memoryview,
                            'min': min,
                            'next': next,
                            'object': object,
                            'oct': oct,
                            'ord': ord,
                            'pow': pow,
                            'print': print,
                            'property': property,
                            'range': range,
                            'repr': repr,
                            'reversed': reversed,
                            'round': round,
                            'set': set,
                            'setattr': setattr,
                            'slice': slice,
                            'sorted': sorted,
                            'str': str,
                            'sum': sum,
                            'super': super,
                            'tuple': tuple,
                            'type': type,
                            'zip': zip,
                        },
                    }
                    local_scope = {'max_leds': max_leds}
                    break
        else:
            time.sleep_us(timestep_us + time.ticks_diff(last_ticks_us, time.ticks_us()))
            time_seconds += timestep

        last_ticks_us = time.ticks_us()
        if current_pattern is None:
            pass  # TODO turn all leds off
        else:
            local_scope['time_seconds'] = time_seconds
            for led_index in range(max_leds):
                try:
                    local_scope['led_index'] = led_index
                    exec(script, global_scope, local_scope)
                    length = len(local_scope['result'])
                    if length != 3:
                        raise ValueError(f'function returned {length} values')
                    result = [int(value) for value in local_scope['result']]
                    if any(value < 0 or value > 255 for value in result):
                        raise ValueError(f'result values {result} are not between 0 and 255')
                except Exception as exception:
                    reset = True
                    temp_file = io.StringIO()
                    sys.print_exception(exception, temp_file)
                    current_pattern['error'] = temp_file.getvalue().split('\n', 2)[2]
                    current_pattern['active'] = False
                else:
                    if led_index == 0:
                        led.on() if result[1] > 127 else led.off()
                    # led_strip.set_pixel(led_index, result)  # TODO
                if reset:
                    break

            if not reset:
                pass
                # led_strip.show()  # TODO


_thread.start_new_thread(led_thread, ())

addr = socket.getaddrinfo('0.0.0.0', 80)[0][-1]

s = socket.socket()
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind(addr)
s.listen(1)

print('listening on', addr)

while True:
    cl, addr = s.accept()

    request = HttpRequest(cl.recv(1024))
    print("Request:", request.request_line)

    if request.request_line.startswith('POST') or request.request_line.startswith('DELETE'):
        try:
            post_data = json.loads(request.body)
        except (IndexError, ValueError):
            cl.send('HTTP/1.0 400 Bad Request\r\nContent-type: text/plain\r\n\r\n')
            cl.close()
            continue

        if request.request_line.startswith('DELETE'):
            try:
                del patterns[post_data['id']]
            except KeyError:
                cl.send('HTTP/1.0 400 Bad Request\r\nContent-type: text/plain\r\n\r\n')
                cl.close()
                continue
            else:
                with open('patterns.json', 'w') as file:
                    file.write(json.dumps(patterns))
        elif request.request_line.startswith('POST'):
            json_keys = {
                'active': bool,
                'name': str,
                'author': str,
                'script': str,
            }

            def key_valid(post_data, key, key_type):
                return key in post_data and isinstance(post_data[key], key_type)

            if key_valid(post_data, 'id', str):
                pattern_id = post_data['id']
            else:
                pattern_id = str(random.getrandbits(32))

            # allow partial update if pattern_id already exists
            if pattern_id in patterns or all(key_valid(post_data, key, key_type) for key, key_type in json_keys.items()):
                if pattern_id not in patterns:
                    patterns[pattern_id] = {}
                do_reset = patterns[pattern_id].get('active', False) or post_data.get('active', False)
                for key, key_type in json_keys.items():
                    if key_valid(post_data, key, key_type):
                        if key == 'active' and post_data[key] is True:
                            patterns[pattern_id]['error'] = None
                            for pattern in patterns.values():
                                pattern['active'] = False
                        patterns[pattern_id][key] = post_data[key]

                if do_reset:
                    reset = True

                with open('patterns.json', 'w') as file:
                    file.write(json.dumps(patterns))

        cl.send('HTTP/1.0 200 OK\r\nContent-type: text/plain\r\n\r\n')
        cl.close()
    else:
        cl.send('HTTP/1.0 200 OK\r\nContent-type: text/html\r\n\r\n')
        to_send = html.generate_html(json.dumps(json.dumps(patterns)))
        chunk = 4096
        for i in range(int(len(to_send)/chunk)):
            cl.sendall(to_send[i*chunk:(i+1)*chunk])
            print(gc.mem_free())
        cl.sendall(to_send[(i+1)*chunk:-1])
        cl.close()
        print(gc.mem_free())
