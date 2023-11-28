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
            error_callback: typing.Callable[[typing.Any, str, int, str], typing.NoReturn],
            led_strip: rpi_ws281x.PixelStrip
    ):
        super().__init__()
        self.__queue = queue.Queue(1)
        self.__error_callback = error_callback
        self.__led_strip = led_strip
        self.calls = 0

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

                    if 'result' not in global_scope:
                        raise ValueError(f"'result' not found in pattern script")

                    try:
                        size = len(global_scope['result'])
                    except TypeError:
                        raise TypeError("'result' must be an iterable (e.g. list or tuple)")

                    if size > self.__led_strip.size:
                        raise ValueError(f"'result' ({size}) is bigger than number of LEDs ({self.__led_strip.size})")

                    for led_index, led in enumerate(global_scope['result']):
                        try:
                            led_len = len(led)
                        except TypeError:
                            raise TypeError(f"Each element of 'result' must be an iterable (e.g. list or tuple)")

                        if led_len != 3:
                            raise ValueError(f"Each element of 'result' must contain 3 values")

                        try:
                            led = tuple(int(colour) for colour in led)
                        except (TypeError, ValueError):
                            led = None

                        if led is None or any(colour < 0 or colour > 255 for colour in led):
                            raise ValueError(f'Each R, G, B value must be between 0 and 255')

                        self.__led_strip[led_index] = ((led[0] & 0xff) << 16) | ((led[1] & 0xff) << 8) | (led[2] & 0xff)
                    self.__led_strip.show()
            except BaseException as exception:
                self.__turn_off()
                if current_pattern is not None:
                    traceback_exception = traceback.TracebackException.from_exception(exception)
                    exception_format = list(traceback_exception.format_exception_only())

                    if hasattr(traceback_exception, 'lineno'):
                        line_number = int(traceback_exception.lineno)
                        exception_format = exception_format[1:]
                    else:
                        line_number = int(traceback_exception.stack[-1].lineno)

                    self.__error_callback(
                        current_pattern['id'],
                        exception_format[-1].rstrip(),
                        line_number,
                        ''.join(exception_format).rstrip(),
                    )
                    current_pattern = None

            self.calls += 1

    def stop(self):
        self.__queue.put({'type': 'stop'})
        self.join()
