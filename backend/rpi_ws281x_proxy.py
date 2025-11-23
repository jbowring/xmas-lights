import sys

try:
    from rpi_ws281x import *
except ImportError:
    print("Module 'rpi_ws281x' not found. Using mock implementation.", file=sys.stderr)
    from rpi_ws281x_mock import *