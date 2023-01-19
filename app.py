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
parser.add_argument('--led-count', action='store', required=True, type=int, help='Number of LEDs')
parser.add_argument('--disable-leds', action='store_true', help='Disable LED output')
parser.add_argument('--websocket-test', action='store_true', help='Send websocket updates once per second')
args = parser.parse_args()

connected_websockets = set()
data = {}
PATTERN_FILENAME = pathlib.Path(__file__).parent / "patterns.json"


def read_patterns_file():
    global PATTERN_FILENAME
    global data

    try:
        with open(PATTERN_FILENAME) as file:
            data = json.load(file)
    except (OSError, ValueError):
        pass


def write_patterns_file():
    global PATTERN_FILENAME
    global data

    with open(PATTERN_FILENAME, 'w') as file:
        json.dump(data, file, indent=2, default=json_serialise)


def json_serialise(_object):
    if isinstance(_object, datetime.datetime):
        return _object.isoformat()
    else:
        raise TypeError(f'Object of type {_object.__class__.__name__}  is not JSON serializable')


def delete_pattern(request, schedule_queue):
    global data
    global PATTERN_FILENAME

    try:
        pattern_id = request['id']
        if data['patterns'][pattern_id].get('active', False):
            schedule_queue.put_nowait('pattern update')
        del data['patterns'][pattern_id]
    except KeyError:
        return "Invalid Pattern ID", 400  # TODO handle error
    else:
        write_patterns_file()
        websockets.broadcast(connected_websockets, json.dumps(data, default=json_serialise))


def update_pattern(request, schedule_queue):
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
            schedule_queue.put_nowait('pattern update')

        write_patterns_file()
        websockets.broadcast(connected_websockets, json.dumps(data, default=json_serialise))

    else:
        return "Incomplete request", 400  # TODO handle error


async def websocket_handler(websocket, schedule_queue):
    connected_websockets.add(websocket)
    try:
        await websocket.send(json.dumps(data, default=json_serialise))
        async for message in websocket:
            request = json.loads(message)
            if all(key in request for key in ['action', 'pattern']):
                if request['action'] == 'create':
                    update_pattern(request['pattern'], schedule_queue)
                elif request['action'] == 'update':
                    update_pattern(request['pattern'], schedule_queue)
                elif request['action'] == 'delete':
                    delete_pattern(request['pattern'], schedule_queue)
    except websockets.ConnectionClosedError:
        pass
    finally:
        connected_websockets.remove(websocket)


async def run_schedule(schedule_queue):
    global data

    if 'schedule' not in data:
        data['schedule'] = {}
    if 'events' not in data['schedule']:
        data['schedule']['events'] = []

    loop = asyncio.get_running_loop()
    led_thread = LEDThread(
        error_callback=lambda pattern_id, error: loop.call_soon_threadsafe(
            process_error,
            pattern_id,
            error
        ),
        led_strip=rpi_ws281x.PixelStrip(args.led_count, 18, strip_type=rpi_ws281x.WS2811_STRIP_GRB)
    )

    if not args.disable_leds:
        signal.signal(signal.SIGINT, lambda signum, frame: [led_thread.stop(), sys.exit()])
        led_thread.start()
        os.nice(1)  # avoid slowing down the rest of the system

    while True:
        now = datetime.datetime.now()

        events = data['schedule']['events']

        for event in events:
            event['next_datetime'] = datetime.datetime.combine(
                date=now.date() + datetime.timedelta(days=(event['day'] - now.weekday()) % 7),
                time=datetime.time(event['hour'], event['minute'])
            )

            if event['next_datetime'] < now:
                event['next_datetime'] += datetime.timedelta(days=7)

        events.sort(key=lambda event: event['next_datetime'])

        on = (len(events) < 1) or (events[-1]['action'] == 'on')

        tomorrow = datetime.datetime.combine(now.date() + datetime.timedelta(days=1), datetime.time.min)

        data['schedule']['status'] = 'on' if on else 'off'
        data['schedule']['today_weekday'] = now.weekday()
        data['schedule']['tomorrow_weekday'] = tomorrow.weekday()

        websockets.broadcast(connected_websockets, json.dumps(
            {
                'schedule': data['schedule']
            },
            default=json_serialise,
        ))

        while True:
            if on and any(pattern['active'] for pattern in data['patterns'].values()):
                for pattern_id, pattern in data['patterns'].items():
                    if pattern['active']:
                        led_thread.set_pattern(pattern | {'id': pattern_id})
                        break
            else:
                led_thread.clear_pattern()

            try:
                if len(events) > 0:
                    time_to_wakeup = min(events[0]['next_datetime'], tomorrow)
                    message = await asyncio.wait_for(
                        schedule_queue.get(),
                        (time_to_wakeup - datetime.datetime.now()).total_seconds()
                    )
                else:
                    message = await schedule_queue.get()

                if message == 'schedule update':
                    break
            except asyncio.exceptions.TimeoutError:
                break


def process_error(pattern_id, error):
    try:
        data['patterns'][pattern_id] |= {
            'error': error,
            'active': False,
        }
    except KeyError:
        pass
    else:
        write_patterns_file()
        websockets.broadcast(connected_websockets, json.dumps(data, default=json_serialise))


async def websockets_test():
    try:
        i = 0
        while True:
            data['patterns']['websocket_test'] = {
                'active': False,
                'name': '_websockets test_',
                'author': str(i),
                'script': str(i),
            }
            websockets.broadcast(connected_websockets, json.dumps(data, default=json_serialise))
            await asyncio.sleep(1)
            i += 1
    finally:
        try:
            del data['patterns']['websocket_test']
        except KeyError:
            pass
        write_patterns_file()


async def main():
    read_patterns_file()
    schedule_queue = asyncio.Queue()

    async def websocket_wrapper(websocket):
        await websocket_handler(websocket, schedule_queue)

    async with websockets.unix_serve(websocket_wrapper, "/tmp/xmas-lights.ws.sock"):
        asyncio.create_task(run_schedule(schedule_queue))

        if args.websocket_test:
            await websockets_test()
        else:
            await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
