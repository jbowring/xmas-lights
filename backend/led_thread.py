import math
import queue
import random
import rpi_ws281x_proxy as rpi_ws281x
import threading
import time
import traceback
import typing
import numpy
import requests


class _ScriptException(Exception):
    def __init__(self, exception):
        super().__init__(self)
        self.exception = exception


class LEDThread(threading.Thread):
    def __init__(
            self,
            *,
            error_callback: typing.Callable[[typing.Any, str, int, str], typing.NoReturn],
            led_strip: rpi_ws281x.PixelStrip,
            external_globals: dict[str, typing.Callable] = None,
    ):
        super().__init__()
        self.__queue = queue.Queue()
        self.__error_callback = error_callback
        self.__led_strip = led_strip
        self.calls = 0

        self.__led_strip.begin()

        # Global scope for script interpretation
        self.GLOBAL_SCOPE = {
            'math': math,
            'random': random,
            'numpy': numpy,
            'np': numpy,
            'requests': requests,
            '__builtins__': {
                'ArithmeticError': ArithmeticError,
                'AssertionError': AssertionError,
                'AttributeError': AttributeError,
                'BaseException': BaseException,
                'BaseExceptionGroup': BaseExceptionGroup,
                'BlockingIOError': BlockingIOError,
                'BrokenPipeError': BrokenPipeError,
                'BufferError': BufferError,
                'BytesWarning': BytesWarning,
                'ChildProcessError': ChildProcessError,
                'ConnectionAbortedError': ConnectionAbortedError,
                'ConnectionError': ConnectionError,
                'ConnectionRefusedError': ConnectionRefusedError,
                'ConnectionResetError': ConnectionResetError,
                'DeprecationWarning': DeprecationWarning,
                'EOFError': EOFError,
                'EncodingWarning': EncodingWarning,
                'EnvironmentError': EnvironmentError,
                'Exception': Exception,
                'ExceptionGroup': ExceptionGroup,
                'FileExistsError': FileExistsError,
                'FileNotFoundError': FileNotFoundError,
                'FloatingPointError': FloatingPointError,
                'FutureWarning': FutureWarning,
                'GeneratorExit': GeneratorExit,
                'IOError': IOError,
                'ImportError': ImportError,
                'ImportWarning': ImportWarning,
                'IndentationError': IndentationError,
                'IndexError': IndexError,
                'InterruptedError': InterruptedError,
                'IsADirectoryError': IsADirectoryError,
                'KeyError': KeyError,
                'KeyboardInterrupt': KeyboardInterrupt,
                'LookupError': LookupError,
                'MemoryError': MemoryError,
                'ModuleNotFoundError': ModuleNotFoundError,
                'NameError': NameError,
                'NotADirectoryError': NotADirectoryError,
                'NotImplemented': NotImplemented,
                'NotImplementedError': NotImplementedError,
                'OSError': OSError,
                'OverflowError': OverflowError,
                'PendingDeprecationWarning': PendingDeprecationWarning,
                'PermissionError': PermissionError,
                'ProcessLookupError': ProcessLookupError,
                'RecursionError': RecursionError,
                'ReferenceError': ReferenceError,
                'ResourceWarning': ResourceWarning,
                'RuntimeError': RuntimeError,
                'RuntimeWarning': RuntimeWarning,
                'StopAsyncIteration': StopAsyncIteration,
                'StopIteration': StopIteration,
                'SyntaxError': SyntaxError,
                'SyntaxWarning': SyntaxWarning,
                'SystemError': SystemError,
                'SystemExit': SystemExit,
                'TabError': TabError,
                'TimeoutError': TimeoutError,
                'TypeError': TypeError,
                'UnboundLocalError': UnboundLocalError,
                'UnicodeDecodeError': UnicodeDecodeError,
                'UnicodeEncodeError': UnicodeEncodeError,
                'UnicodeError': UnicodeError,
                'UnicodeTranslateError': UnicodeTranslateError,
                'UnicodeWarning': UnicodeWarning,
                'UserWarning': UserWarning,
                'ValueError': ValueError,
                'Warning': Warning,
                'ZeroDivisionError': ZeroDivisionError,
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
                'classmethod': classmethod,
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
                'staticmethod': staticmethod,
                'str': str,
                'sum': sum,
                'super': super,
                'tuple': tuple,
                'type': type,
                'zip': zip,
            },
            'max_leds': self.__led_strip.numPixels(),
            't': 0.0,
        }

        if external_globals is not None:
            self.GLOBAL_SCOPE |= external_globals

    def set_pattern(self, pattern_id, pattern):
        if self.is_alive():
            self.__queue.put({
                'type': 'pattern',
                'payload': pattern | {'id': pattern_id},
            })

    def clear_pattern(self):
        if self.is_alive():
            self.__queue.put({
                'type': 'pattern',
                'payload': None,
            })

    def enable(self, enabled):
        if self.is_alive():
            self.__queue.put({
                'type': 'enable',
                'payload': bool(enabled),
            })

    def __turn_off(self):
        for led_index in range(self.__led_strip.numPixels()):
            self.__led_strip.setPixelColor(led_index, 0)
        self.__led_strip.show()
        self.calls = 0

    def run(self) -> None:
        current_pattern = None
        enabled = False
        script = None
        start_time = 0
        global_scope = {}
        self.__turn_off()

        while True:
            # noinspection PyBroadException
            try:
                try:
                    message = self.__queue.get(not enabled or current_pattern is None)
                except queue.Empty:
                    global_scope['t'] = time.monotonic() - start_time
                else:
                    match message['type']:
                        case 'pattern':
                            current_pattern = message['payload']
                            try:
                                script = compile(current_pattern['script'], current_pattern['name'], 'exec')
                            except BaseException as exception:
                                raise _ScriptException(exception)

                            global_scope = self.GLOBAL_SCOPE.copy()
                            start_time = time.monotonic()
                        case 'enable':
                            enabled = message['payload']
                        case 'stop':
                            self.__turn_off()
                            break

                if not enabled or current_pattern is None:
                    self.__turn_off()
                else:
                    try:
                        exec(script, global_scope)
                    except BaseException as exception:
                        raise _ScriptException(exception)

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
                    if isinstance(exception, _ScriptException):
                        traceback_exception = traceback.TracebackException.from_exception(exception.exception)
                    else:
                        traceback_exception = traceback.TracebackException.from_exception(exception)

                    exception_format = list(traceback_exception.format_exception_only())

                    if isinstance(exception, _ScriptException):
                        if hasattr(traceback_exception, 'lineno'):
                            line_number = int(traceback_exception.lineno)
                            exception_format = exception_format[1:]
                        else:
                            line_number = int(traceback_exception.stack[-1].lineno)

                        mark_message = ''.join(exception_format).rstrip()
                    else:
                        line_number = None
                        mark_message = None                        

                    self.__error_callback(
                        current_pattern['id'],
                        exception_format[-1].rstrip(),
                        line_number,
                        mark_message,
                    )
                    current_pattern = None

            self.calls += 1

    def stop(self):
        self.__queue.put({'type': 'stop'})
        if self.is_alive():
            self.join()
