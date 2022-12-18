import math
import random
import time
import json
from pathlib import Path
import threading
import traceback

from flask import Flask, request, abort

import app_html


max_leds = 40
# led_strip = neopixel.NeoPixel(max_leds, 0, 22, 'GRB')  # TODO

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
    }
}


reset = True

patterns = {}

try:
    pattern_filename = Path(__file__).parent / "patterns.json"
    with open(pattern_filename) as file:
        patterns = json.loads(file.read())
except (OSError, ValueError):
    pass



def led_thread():
    global reset
    global patterns
    global max_leds
    current_pattern = None
    script = None
    time_seconds = 0
    timestep = 0.1

    # led = ... TODO: Actually set LEDs

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
                    try:
                        script = compile(current_pattern['script'], current_pattern['name'], 'exec')
                    except SyntaxError as e:
                        pattern['active'] = False
                        pattern['error'] = str(e) # TODO: Get e.line and highlight in GUI
                        current_pattern = None
                    local_scope = {'max_leds': max_leds}
                    break
        else:
            time.sleep(timestep)
            time_seconds += timestep

        if current_pattern is None:
            #led = 
            pass  # TODO turn all leds off
        else:
            local_scope['time_seconds'] = time_seconds
            for led_index in range(max_leds):
                try:
                    local_scope['led_index'] = led_index
                    exec(script, GLOBAL_SCOPE, local_scope)
                    length = len(local_scope['result'])
                    if length != 3:
                        raise ValueError(f'function returned {length} values')
                    result = [int(value) for value in local_scope['result']]
                    if any(value < 0 or value > 255 for value in result):
                        raise ValueError(f'result values {result} are not between 0 and 255')
                except Exception as exception:
                    reset = True
                    error_string = traceback.format_exc(limit=3)
                    current_pattern['error'] = error_string
                    current_pattern['active'] = False
                else:
                    if led_index == 0:
                        # led.on() if result[1] > 127 else led.off()
                        pass
                    # led_strip.set_pixel(led_index, result)  # TODO
                if reset:
                    break

            if not reset:
                pass
                # led_strip.show()  # TODO

app = Flask(__name__)

@app.route("/",methods=['GET'])
def home():
    global patterns
    return app_html.generate_html(json.dumps(json.dumps(patterns)))
    
@app.route("/", methods=['POST', 'DELETE'])
def update_pattern():
        global reset
        global patterns

        if request.method == 'DELETE':
            try:
                del patterns[post_data['id']]
            except KeyError:
                return ("Invalid Pattern ID", 400)
            else:
                with open('patterns.json', 'w') as file:
                    file.write(json.dumps(patterns))
            return "OK"

        elif request.method == 'POST':
            json_keys = {
                'active': bool,
                'name': str,
                'author': str,
                'script': str,
            }

            post_data = request.json

            def key_valid(post_data, key, key_type):
                return key in post_data and isinstance(post_data[key], key_type)

            if key_valid(post_data, 'id', str):
                pattern_id = request.json['id']
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

            return "OK"
    

if __name__=="__main__":
    threading.Thread(target=led_thread).start()
    app.run(host="0.0.0.0",debug=False, threaded=True)
