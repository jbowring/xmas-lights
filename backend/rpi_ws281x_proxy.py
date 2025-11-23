import sys

try:
    from rpi_ws281x import *  # noqa F403
except ImportError:
    print("Module 'rpi_ws281x' not found. Using mock implementation.", file=sys.stderr)
    from rpi_ws281x_mock import *  # noqa F403
