import argparse
import asyncio
import datetime
import importlib
import json
import os
import pathlib
import random
import signal
import sys
import time
import typing

import pydantic
import pydantic_settings
import websockets

import led_thread
import plugins.teams.plugin
import plugins.plugin
import rpi_ws281x_proxy as rpi_ws281x
from led_thread import LEDThread

CONFIG_ENV_VAR='XMAS_LIGHTS_CONFIG'
UNIX_SOCKET_PATH = '/tmp/xmas-lights.ws.sock'
DEFAULT_DIR = '/var/lib/xmas-lights'

patterns_file = f'{DEFAULT_DIR}/patterns.json'
connected_websockets = set()
data = {}
schedule_timer_handle = None

class PluginsConfig(pydantic.BaseModel):
    teams: typing.Optional[plugins.teams.plugin.Config] = None

class AppConfig(pydantic_settings.BaseSettings):
    led_count: int
    patterns_file: str = patterns_file
    plugins_dir: str = f'{DEFAULT_DIR}/plugins/'
    port: typing.Optional[int] = None
    disable_leds: bool = False
    websocket_test: bool = False

    plugins: PluginsConfig = pydantic.Field(default_factory=PluginsConfig)

    model_config = pydantic_settings.SettingsConfigDict(
        env_prefix='XMAS_LIGHTS_'
    )

    @classmethod
    def settings_customise_sources(
            cls,
            settings_cls: typing.Type[pydantic_settings.BaseSettings],
            init_settings: pydantic_settings.PydanticBaseSettingsSource,
            env_settings: pydantic_settings.PydanticBaseSettingsSource,
            dotenv_settings: pydantic_settings.PydanticBaseSettingsSource,
            file_secret_settings: pydantic_settings.PydanticBaseSettingsSource,
    ) -> tuple[pydantic_settings.PydanticBaseSettingsSource, ...]:
        return (
            init_settings,
            env_settings,
            dotenv_settings,
            pydantic_settings.TomlConfigSettingsSource(settings_cls),
            file_secret_settings,
        )

def read_patterns_file():
    global patterns_file
    global data

    # open file with write permissions to error out immediately
    with open(patterns_file, 'a+') as file:
        file.seek(0)
        text = file.read()

        # prevent error when opening empty file
        if len(text.strip()) > 0:
            data = json.loads(text)

    # convert legacy error messages into new
    if 'patterns' in data:
        for pattern in data['patterns'].values():
            if 'error' in pattern and type(pattern['error']) is str:
                pattern['error'] = {
                    'home_popover': pattern['error'],
                }
    else:
        data['patterns'] = {}


def write_patterns_file():
    global patterns_file
    global data

    with open(patterns_file, 'w') as file:
        json.dump(data, file, indent=2, default=json_serialise)


def json_serialise(_object):
    if isinstance(_object, datetime.datetime):
        return _object.isoformat()
    else:
        raise TypeError(f'Object of type {_object.__class__.__name__}  is not JSON serializable')


def delete_pattern(request, led_thread):
    global data

    try:
        pattern_id = request['id']
        if data['patterns'][pattern_id].get('active', False):
            led_thread.clear_pattern()
        del data['patterns'][pattern_id]
    except KeyError:
        pass
        # return "Invalid Pattern ID", 400  # TODO handle error
    else:
        write_patterns_file()
        websockets.broadcast(connected_websockets, json.dumps(data, default=json_serialise))


def update_pattern(request, led_thread):
    global data

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
        pattern = patterns[pattern_id]

        update = pattern.get('active', False) or request.get('active', False)
        for key, key_type in json_keys.items():
            if key_valid(request, key, key_type):
                pattern_active = key == 'active' and request[key] is True
                pattern_script_changed = key == 'script' and request[key] != pattern.get(key)

                if pattern_active or pattern_script_changed:
                    pattern['error'] = None

                if pattern_active:
                    for other_pattern in patterns.values():
                        other_pattern['active'] = False
                pattern[key] = request[key]

        if update:
            if pattern['active']:
                led_thread.set_pattern(pattern_id, pattern)
            else:
                led_thread.clear_pattern()

        write_patterns_file()
        websockets.broadcast(connected_websockets, json.dumps(data, default=json_serialise))

    else:
        pass
        # return "Incomplete request", 400  # TODO handle error


async def websocket_handler(websocket: websockets.WebSocketServerProtocol, led_thread: led_thread.LEDThread):
    connected_websockets.add(websocket)
    try:
        await websocket.send(json.dumps(data, default=json_serialise))
        async for message in websocket:
            request = json.loads(message)
            if all(key in request for key in ['action', 'payload']):
                if request['action'] == 'create_pattern':
                    update_pattern(request['payload'], led_thread)
                elif request['action'] == 'update_pattern':
                    update_pattern(request['payload'], led_thread)
                elif request['action'] == 'delete_pattern':
                    delete_pattern(request['payload'], led_thread)
                elif request['action'] == 'update_schedule':
                    if 'events' in request['payload']:
                        data['schedule']['events'] = request['payload']['events']
                        do_schedule(led_thread)
                        write_patterns_file()
    except websockets.ConnectionClosedError:
        pass
    finally:
        connected_websockets.remove(websocket)


async def get_update_rate(led_thread):
    data['update_rate'] = 0

    last_update = None
    led_thread.calls = 0

    while True:
        calls = led_thread.calls

        if last_update is None:
            data['update_rate'] = 0
        else:
            data['update_rate'] = int(calls / (time.monotonic() - last_update))

        led_thread.calls = 0

        if calls == 0:
            last_update = None
        else:
            last_update = time.monotonic()

        websockets.broadcast(connected_websockets, json.dumps(
            {
                'update_rate': data.get('update_rate', 0)
            },
            default=json_serialise,
        ))

        await asyncio.sleep(1)


def do_schedule(led_thread):
    global data, schedule_timer_handle

    if 'schedule' not in data:
        data['schedule'] = {}
    if 'events' not in data['schedule']:
        data['schedule']['events'] = []

    now = datetime.datetime.now()

    events = data['schedule']['events']

    for event in events:
        event['next_datetime'] = datetime.datetime.combine(
            date=now.date() + datetime.timedelta(days=(event['day'] - now.weekday()) % 7),
            time=datetime.time(event['hour'], event['minute'])
        )

        if event['next_datetime'] < now:
            event['next_datetime'] += datetime.timedelta(days=7)

    events.sort(key=lambda x: x['next_datetime'])

    on = (len(events) < 1) or (events[-1]['action'] == 'on')

    tomorrow = datetime.datetime.combine(now.date() + datetime.timedelta(days=1), datetime.time.min)

    data['schedule']['status'] = 'on' if on else 'off'
    data['schedule']['today_weekday'] = now.weekday()
    data['schedule']['tomorrow_weekday'] = tomorrow.weekday()

    led_thread.enable(on)

    websockets.broadcast(connected_websockets, json.dumps(
        {
            'schedule': data['schedule']
        },
        default=json_serialise,
    ))

    if schedule_timer_handle is not None:
        schedule_timer_handle.cancel()

    if len(events) > 0:
        schedule_timer_handle = asyncio.get_running_loop().call_later(
            (min(events[0]['next_datetime'], tomorrow) - datetime.datetime.now()).total_seconds(),
            do_schedule,
            led_thread,
        )


def process_error(pattern_id, home_popover, line_number, mark_message):
    try:
        data['patterns'][pattern_id] |= {
            'error': {
                'home_popover': home_popover,
                'line_number': line_number,
                'mark_message': mark_message,
            },
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


async def main(config: AppConfig):
    global patterns_file
    patterns_file = config.patterns_file
    pathlib.Path(patterns_file).parent.mkdir(parents=True, exist_ok=True)
    read_patterns_file()

    active_plugins: list[plugins.plugin.Plugin] = []
    external_globals = {}
    for name, plugin_config in config.plugins:
        if plugin_config is not None and plugin_config.enabled:
            plugin_path = pathlib.Path(config.plugins_dir, name)
            plugin_path.mkdir(parents=True, exist_ok=True)
            plugin_thread = importlib.import_module(f'plugins.{name}.plugin').Plugin(plugin_path, plugin_config)

            external_globals |= plugin_thread.get_exports()
            plugin_thread.start()
            active_plugins.append(plugin_thread)

    loop = asyncio.get_running_loop()
    led_thread = LEDThread(
        error_callback=lambda pattern_id, home_popover, line_number, mark_message: loop.call_soon_threadsafe(
            process_error,
            pattern_id,
            home_popover,
            line_number,
            mark_message,
        ),
        led_strip=rpi_ws281x.PixelStrip(config.led_count, 18, strip_type=rpi_ws281x.WS2811_STRIP_RGB),
        external_globals=external_globals,
    )

    # noinspection PyUnusedLocal
    def stop(signum, frame):
        for plugin_thread in active_plugins:
            plugin_thread.stop()

        if led_thread.is_alive():
            led_thread.stop()
        sys.exit()

    signal.signal(signal.SIGINT, stop)

    if not config.disable_leds:
        led_thread.start()
        asyncio.create_task(get_update_rate(led_thread))

    async def websocket_wrapper(websocket: websockets.WebSocketServerProtocol):
        await websocket_handler(websocket, led_thread)

    if config.port is None:
        server = websockets.unix_serve(websocket_wrapper, UNIX_SOCKET_PATH)
    else:
        server = websockets.serve(websocket_wrapper, 'localhost', config.port)

    async with server:
        do_schedule(led_thread)

        if any(pattern['active'] for pattern in data['patterns'].values()):
            for pattern_id, pattern in data['patterns'].items():
                if pattern['active']:
                    led_thread.set_pattern(pattern_id, pattern)

        if config.websocket_test:
            await websockets_test()
        else:
            await asyncio.Future()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--config',
        action='store',
        default=os.environ.get('XMAS_LIGHTS_CONFIG', '/var/lib/xmas-lights/config.toml'),
        help=f'Path to configuration file (default: %(default)s)'
    )
    args = parser.parse_args()

    if not os.path.exists(args.config):
        print(f"Configuration file not found at: {args.config}", file=sys.stderr)
        sys.exit(1)

    AppConfig.model_config['toml_file'] = args.config

    # noinspection PyArgumentList
    asyncio.run(main(AppConfig()))
