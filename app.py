#!/usr/bin/python

import random
import sys
import json
import pathlib
import rpi_ws281x
import websockets
import asyncio
import argparse
import os
import signal
import datetime
from led_thread import LEDThread

parser = argparse.ArgumentParser()
parser.add_argument('--websocket-test', action='store_true', help='Send websocket updates once per second')
parser.add_argument('--disable-leds', action='store_true', help='Disable LED output')
args = parser.parse_args()

connected_websockets = set()
data = {}

PATTERN_FILENAME = pathlib.Path(__file__).parent / "patterns.json"

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


def delete_pattern(request, led_thread):
    global data
    global PATTERN_FILENAME

    try:
        pattern_id = request['id']
        if data['patterns'][pattern_id].get('active', False):
            led_thread.clear_pattern()
        del data['patterns'][pattern_id]
    except KeyError:
        return "Invalid Pattern ID", 400  # TODO handle error
    else:
        with open(PATTERN_FILENAME, 'w') as file:
            file.write(json.dumps(data))
        websockets.broadcast(connected_websockets, json.dumps(data))


def update_pattern(request, led_thread):
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
        update = patterns[pattern_id].get('active', False) or request.get('active', False)
        for key, key_type in json_keys.items():
            if key_valid(request, key, key_type):
                if key == 'active' and request[key] is True:
                    patterns[pattern_id]['error'] = None
                    for pattern in patterns.values():
                        pattern['active'] = False
                patterns[pattern_id][key] = request[key]

        if update:
            led_thread.set_pattern(patterns[pattern_id] | {'id': pattern_id})

        with open(PATTERN_FILENAME, 'w') as file:
            file.write(json.dumps(data))
        websockets.broadcast(connected_websockets, json.dumps(data))

    else:
        return "Incomplete request", 400  # TODO handle error


async def websocket_handler(websocket, led_thread):
    connected_websockets.add(websocket)
    try:
        await websocket.send(json.dumps(data))
        async for message in websocket:
            request = json.loads(message)
            if all(key in request for key in ['action', 'pattern']):
                if request['action'] == 'create':
                    update_pattern(request['pattern'], led_thread)
                elif request['action'] == 'update':
                    update_pattern(request['pattern'], led_thread)
                elif request['action'] == 'delete':
                    delete_pattern(request['pattern'], led_thread)
    except websockets.ConnectionClosedError:
        pass
    finally:
        connected_websockets.remove(websocket)


async def main():
    led_thread = LEDThread(
        event_loop=asyncio.get_running_loop(),
        error_callback=process_error,
        led_strip=rpi_ws281x.PixelStrip(40, 18, strip_type=rpi_ws281x.WS2811_STRIP_GRB)
    )

    async def websocket_wrapper(websocket):
        await websocket_handler(websocket, led_thread)

    # async with websockets.unix_serve(handler, "/tmp/xmas-lights.ws.sock"):
    async with websockets.serve(websocket_wrapper, "localhost", 5000):
        if not args.disable_leds:
            signal.signal(signal.SIGINT, lambda signum, frame: [led_thread.stop(), sys.exit()])
            led_thread.start()
            os.nice(1)  # avoid slowing down the rest of the system

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


def process_error(pattern_id, error):
    try:
        data['patterns'][pattern_id] |= {
            'error': error,
            'active': False,
        }
    except KeyError:
        pass
    else:
        with open(PATTERN_FILENAME, 'w') as file:
            file.write(json.dumps(data))
        websockets.broadcast(connected_websockets, json.dumps(data))


if __name__ == "__main__":
    calculate_schedule()
    asyncio.run(main())
