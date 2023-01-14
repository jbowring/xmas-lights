#!/usr/bin/python

import math
import random
import sys
import time
import json
from pathlib import Path
import threading
import traceback
import websockets
import asyncio
import rpi_ws281x
import argparse
import os
import signal
import datetime

parser = argparse.ArgumentParser()
parser.add_argument('--websocket-test', action='store_true', help='Send websocket updates once per second')
parser.add_argument('--disable-leds', action='store_true', help='Disable LED output')
args = parser.parse_args()

MAX_LEDS = 40

connected_websockets = set()

# Global scope for script interpretation
GLOBAL_SCOPE = {
    'math': math,
    'random': random,
    '__builtins__': {
        '__build_class__': __build_class__,
        '__name__': '',
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
    'max_leds': MAX_LEDS,
    'seconds': 0.0,
}

stop_requested = False
reset = True

data = {}

PATTERN_FILENAME = Path(__file__).parent / "patterns.json"

try:
    with open(PATTERN_FILENAME) as file:
        data = json.loads(file.read())
except (OSError, ValueError):
    pass

schedule = {
    'events': [
        {
            'day': day,
            'hour': 8,
            'minute': 45,
            'action': 'on',
        } for day in range(5)] + [
        {
            'day': day,
            'hour': 18,
            'minute': 30,
            'action': 'off',
        } for day in range(5)]
}


def led_thread():
    global reset
    global data
    global MAX_LEDS
    global stop_requested

    current_pattern = None
    script = None
    start_time = 0
    global_scope = {}
    led_strip = rpi_ws281x.PixelStrip(MAX_LEDS, 18, strip_type=rpi_ws281x.WS2811_STRIP_GRB)
    led_strip.begin()

    while not stop_requested:
        try:
            if reset:
                reset = False
                current_pattern = None
                for pattern in data['patterns'].values():
                    if pattern['active']:
                        current_pattern = pattern
                        current_pattern['error'] = None
                        script = compile(current_pattern['script'], current_pattern['name'], 'exec')
                        global_scope = dict(GLOBAL_SCOPE)
                        start_time = time.monotonic()
                        break
            else:
                global_scope['seconds'] = time.monotonic() - start_time

            if current_pattern is None:
                for led_index in range(MAX_LEDS):
                    led_strip.setPixelColor(led_index, 0)
            else:
                exec(script, global_scope)
                for led_index in range(MAX_LEDS):
                    led_strip.setPixelColor(led_index, rpi_ws281x.Color(*(int(global_scope['result'][led_index][i]) for i in range(3))))
            led_strip.show()
        except Exception as exception:
            reset = True
            if current_pattern is not None:
                current_pattern['error'] = traceback.format_exc(limit=3).split('\n', 3)[3]  # TODO: Get e.line and highlight in GUI
                current_pattern['active'] = False


def delete_pattern(request):
    global reset
    global data
    global PATTERN_FILENAME

    try:
        pattern_id = request['id']
        do_reset = data['patterns'][pattern_id].get('active', False)
        del data['patterns'][pattern_id]
        if do_reset:
            reset = True
    except KeyError:
        return "Invalid Pattern ID", 400  # TODO handle error
    else:
        with open(PATTERN_FILENAME, 'w') as file:
            file.write(json.dumps(data))
        websockets.broadcast(connected_websockets, json.dumps(data))


def update_pattern(request):
    global reset
    global data
    global PATTERN_FILENAME

    json_keys = {
        'active': bool,
        'name': str,
        'author': str,
        'script': str,
    }

    def key_valid(post_data, key, key_type):
        return key in post_data and isinstance(post_data[key], key_type)

    if key_valid(request, 'id', str):
        pattern_id = request['id']
    else:
        pattern_id = str(random.getrandbits(32))

    patterns = data['patterns']

    # allow partial update if pattern_id already exists
    if pattern_id in patterns or all(key_valid(request, key, key_type) for key, key_type in json_keys.items()):
        if pattern_id not in patterns:
            patterns[pattern_id] = {}
        do_reset = patterns[pattern_id].get('active', False) or request.get('active', False)
        for key, key_type in json_keys.items():
            if key_valid(request, key, key_type):
                if key == 'active' and request[key] is True:
                    patterns[pattern_id]['error'] = None
                    for pattern in patterns.values():
                        pattern['active'] = False
                patterns[pattern_id][key] = request[key]

        if do_reset:
            reset = True

        with open(PATTERN_FILENAME, 'w') as file:
            file.write(json.dumps(data))
        websockets.broadcast(connected_websockets, json.dumps(data))

    else:
        return "Incomplete request", 400  # TODO handle error


async def handler(websocket):
    connected_websockets.add(websocket)
    try:
        await websocket.send(json.dumps(data))
        async for message in websocket:
            request = json.loads(message)
            if all(key in request for key in ['action', 'pattern']):
                if request['action'] == 'create':
                    update_pattern(request['pattern'])
                elif request['action'] == 'update':
                    update_pattern(request['pattern'])
                elif request['action'] == 'delete':
                    delete_pattern(request['pattern'])
    except websockets.ConnectionClosedError:
        pass
    finally:
        connected_websockets.remove(websocket)


async def main():
    # async with websockets.unix_serve(handler, "/tmp/xmas-lights.ws.sock"):
    async with websockets.serve(handler, "localhost", 5000):
        if args.websocket_test:
            try:
                i = 0
                while True:
                    data['patterns']['websocket_test'] = {
                        'name': '_websockets test_',
                        'author': str(i),
                        'script': str(i),
                    }
                    websockets.broadcast(connected_websockets, json.dumps(data))
                    await asyncio.sleep(1)
                    i += 1
            finally:
                try:
                    del data['patterns']['websocket_test']
                except KeyError:
                    pass
                with open(PATTERN_FILENAME, 'w') as file:
                    file.write(json.dumps(data))
        else:
            await asyncio.Future()


def calculate_schedule():
    global data

    def date_seconds(weekday, hour, minute, second=0):
        return (((((weekday * 24) + hour) * 60) + minute) * 60) + second

    now = datetime.datetime.utcnow()
    now_seconds = date_seconds(now.weekday(), now.hour, now.minute, now.second)
    week_seconds = date_seconds(6, 24, 60, 60)

    def to_seconds_from_now(event):
        return (date_seconds(event['day'], event['hour'], event['minute']) - now_seconds) % week_seconds

    data['events'].sort(key=to_seconds_from_now)
    print(data['events'])


def signal_handler(signum, frame):
    global stop_requested
    stop_requested = True
    sys.exit()


signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)

if __name__ == "__main__":
    calculate_schedule()
    if not args.disable_leds:
        threading.Thread(target=led_thread).start()
        os.nice(1)  # avoid slowing down the rest of the system
    asyncio.run(main())
