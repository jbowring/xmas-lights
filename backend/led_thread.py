import math
import queue
import random
import rpi_ws281x
import threading
import time
import traceback
import typing


class LEDThread(threading.Thread):
    def __init__(
            self,
            *,
            error_callback: typing.Callable[[typing.Any, typing.Any], typing.Any],
            led_strip: rpi_ws281x.PixelStrip
    ):
        super().__init__()
        self.__queue = queue.Queue(1)
        self.__error_callback = error_callback
        self.__led_strip = led_strip

        self.__led_strip.begin()

        # Global scope for script interpretation
        self.GLOBAL_SCOPE = {
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
            'max_leds': self.__led_strip.numPixels(),
            'seconds': 0.0,
        }

    def set_pattern(self, pattern):
        try:
            self.__queue.get_nowait()
        except queue.Empty:
            pass

        self.__queue.put({
            'type': 'pattern',
            'payload': pattern,
        })

    def clear_pattern(self):
        self.set_pattern(None)

    def __turn_off(self):
        for led_index in range(self.__led_strip.numPixels()):
            self.__led_strip.setPixelColor(led_index, 0)
        self.__led_strip.show()

    def run(self) -> None:
        current_pattern = None
        script = None
        start_time = 0
        global_scope = {}
        self.__turn_off()

        while True:
            # noinspection PyBroadException
            try:
                try:
                    message = self.__queue.get(current_pattern is None)
                    if message['type'] == 'pattern':
                        current_pattern = message['payload']
                    elif message['type'] == 'stop':
                        self.__turn_off()
                        break
                except queue.Empty:
                    global_scope['seconds'] = time.monotonic() - start_time
                else:
                    script = compile(current_pattern['script'], current_pattern['name'], 'exec')
                    global_scope = dict(self.GLOBAL_SCOPE)
                    start_time = time.monotonic()

                if current_pattern is None:
                    self.__turn_off()
                else:
                    exec(script, global_scope)
                    for led_index in range(self.__led_strip.numPixels()):
                        self.__led_strip.setPixelColor(
                            led_index,
                            rpi_ws281x.Color(*(int(global_scope['result'][led_index][i]) for i in range(3)))
                        )
                    self.__led_strip.show()
            except Exception:
                self.__turn_off()
                if current_pattern is not None:
                    # TODO: Get error line and highlight in GUI
                    self.__error_callback(
                        current_pattern['id'],
                        traceback.format_exc(limit=3).split('\n', 3)[3]
                    )
                    current_pattern = None

    def stop(self):
        self.__queue.put({'type': 'stop'})
        self.join()
