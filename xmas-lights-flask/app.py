#!/usr/bin/python

import math
import random
import time
import json
from pathlib import Path
import threading
import traceback

from flask import Flask, request, abort
import rpi_ws281x

import app_html

max_leds = 40
led_strip = rpi_ws281x.PixelStrip(max_leds, 18, strip_type=rpi_ws281x.WS2811_STRIP_GRB)
led_strip.begin()

timestep = 0.1

# Global scope for script interpretation
GLOBAL_SCOPE = {
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
    'max_leds': max_leds,
    'timestep_ms': timestep * 1000,
}

reset = True

patterns = {}

PATTERN_FILENAME = Path(__file__).parent / "patterns.json"

try:
    with open(PATTERN_FILENAME) as file:
        patterns = json.loads(file.read())
except (OSError, ValueError):
    pass


def led_thread():
    global reset
    global patterns
    global max_leds
    global timestep
    current_pattern = None
    script = None
    ticks = 0
    global_scope = {}

    while True:
        try:
            if reset:
                reset = False
                ticks = 0
                current_pattern = None
                script = None
                for pattern in patterns.values():
                    if pattern['active']:
                        current_pattern = pattern
                        current_pattern['error'] = None
                        script = compile(current_pattern['script'], current_pattern['name'], 'exec')
                        global_scope = dict(GLOBAL_SCOPE)
                        break
            else:
                time.sleep(timestep)
                ticks += 1

            if current_pattern is None:
                for led_index in range(max_leds):
                    led_strip.setPixelColor(led_index, 0)
            else:
                global_scope['ticks'] = ticks
                exec(script, global_scope)
                for led_index in range(max_leds):
                    led_strip.setPixelColor(led_index, rpi_ws281x.Color(*(int(value) for value in global_scope['result'][led_index])))
            led_strip.show()
        except Exception as exception:
            reset = True
            if current_pattern is not None:
                current_pattern['error'] = traceback.format_exc(limit=3)  # TODO: Get e.line and highlight in GUI
                current_pattern['active'] = False


app = Flask(__name__)


@app.route("/", methods=['GET'])
def home():
    global patterns
    return app_html.generate_html(json.dumps(json.dumps(patterns)))


@app.route("/", methods=['DELETE'])
def delete_pattern():
    global reset
    global patterns
    global PATTERN_FILENAME

    try:
        pattern_id = request.json['id']
        do_reset = patterns[pattern_id].get('active', False)
        del patterns[pattern_id]
        if do_reset:
            reset = True
    except KeyError:
        return "Invalid Pattern ID", 400
    else:
        with open(PATTERN_FILENAME, 'w') as file:
            file.write(json.dumps(patterns))
        return "OK"


@app.route("/", methods=['POST'])
def update_pattern():
    global reset
    global patterns
    global PATTERN_FILENAME

    json_keys = {
        'active': bool,
        'name': str,
        'author': str,
        'script': str,
    }

    def key_valid(post_data, key, key_type):
        return key in post_data and isinstance(post_data[key], key_type)

    if key_valid(request.json, 'id', str):
        pattern_id = request.json['id']
    else:
        pattern_id = str(random.getrandbits(32))

    # allow partial update if pattern_id already exists
    if pattern_id in patterns or all(key_valid(request.json, key, key_type) for key, key_type in json_keys.items()):
        if pattern_id not in patterns:
            patterns[pattern_id] = {}
        do_reset = patterns[pattern_id].get('active', False) or request.json.get('active', False)
        for key, key_type in json_keys.items():
            if key_valid(request.json, key, key_type):
                if key == 'active' and request.json[key] is True:
                    patterns[pattern_id]['error'] = None
                    for pattern in patterns.values():
                        pattern['active'] = False
                patterns[pattern_id][key] = request.json[key]

        if do_reset:
            reset = True

        with open(PATTERN_FILENAME, 'w') as file:
            file.write(json.dumps(patterns))
        return "OK"

    else:
        return "Incomplete request", 400


if __name__ == "__main__":
    threading.Thread(target=led_thread).start()
    app.run(host="0.0.0.0", debug=False, threaded=True)
