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
import uasyncio

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
        # TODO make async
        request = urequests.get(secrets.ddns_url + f'&myip={ip_address}')
        print(request.content)
        request.close()


reset = True
led = machine.Pin('LED')

patterns = {}

try:
    with open('patterns.json') as file:
        patterns = json.loads(file.read())
except (OSError, ValueError):
    pass

reconnect_wifi()


async def serve_client(reader, writer):
    global reset
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
                do_reset = patterns[pattern_id].get('active', False) or post_data.get('active', False)
                for key, key_type in keys.items():
                    if key in post_data and isinstance(post_data[key], key_type):
                        if key == 'active' and post_data[key] is True:
                            for pattern in patterns.values():
                                pattern['active'] = False
                        patterns[pattern_id][key] = post_data[key]

                if do_reset:
                    reset = True

                with open('patterns.json', 'w') as file:
                    file.write(json.dumps(patterns))

    writer.write('HTTP/1.0 200 OK\r\nContent-type: text/html\r\n\r\n')
    writer.write(html.generate_html(json.dumps(json.dumps(patterns))))
    await writer.drain()
    await writer.wait_closed()


async def main():
    global reset
    print('Setting up webserver...')
    await uasyncio.get_event_loop().create_task(uasyncio.start_server(serve_client, "0.0.0.0", 80))
    current_pattern = None
    time_seconds = 0
    timestep = 0.1

    while True:
        if reset:
            print('reset')  # TODO remove
            reset = False
            time_seconds = 0
            current_pattern = None
            for pattern in patterns.values():
                if pattern['active']:
                    current_pattern = pattern
                    break
        else:
            print('sleeping')  # TODO remove
            await uasyncio.sleep(timestep)
            time_seconds += timestep

        if current_pattern is None:
            pass  # TODO turn all leds off
            print('leds off')  # TODO remove
        else:
            for led_index in range(max_leds):
                try:
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
                    local_scope = {
                        'time_seconds': time_seconds,
                        'led_index': led_index,
                        'max_leds': 40,
                    }
                    script = current_pattern['script']
                    exec(script, global_scope, local_scope)
                    length = len(local_scope['result'])
                    if length != 3:
                        raise ValueError('function returned ' + str(length) + 'value')
                    result = []
                    for i, colour in enumerate(['r', 'g', 'b']):
                        value = int(local_scope['result'][i])
                        if not 0 <= value <= 255:
                            raise ValueError(colour + ' value ' + str(value) + ' must be between 0 and 255')
                        result.append(value)
                except Exception as exception:
                    reset = True
                    current_pattern['error'] = repr(exception)
                    current_pattern = None
                    for pattern in patterns.values():
                        pattern['active'] = False
                    raise  # TODO remove
                else:
                    if led_index == 0:
                        print(result)  # TODO remove
                        led.on() if result[1] > 127 else led.off()
                    # led_strip.set_pixel(led_index, result)  # TODO

                if reset:
                    break
                else:
                    pass
                    # led_strip.show()  # TODO


try:
    uasyncio.run(main())
finally:
    uasyncio.new_event_loop()
