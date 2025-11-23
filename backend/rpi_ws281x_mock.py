WS2811_STRIP_RGB = 0x100800

class PixelStrip:
    def __init__(self, num, pin, *args, **kwargs):
        self.num = num
        self.size = num
        self._led_data = [0] * num
        print(f"[WS2812 mock] Initialized {num} LEDs on pin {pin}")

    # noinspection PyMethodMayBeStatic
    def begin(self):
        print("[WS2812 mock] Strip begin")

    # noinspection PyMethodMayBeStatic
    def show(self):
        print(f"[WS2812 mock] Show")

    # noinspection PyPep8Naming
    def setPixelColor(self, n, color):
        if 0 <= n < self.num:
            self._led_data[n] = color

    # noinspection PyPep8Naming
    def numPixels(self):
        return self.num

    def __setitem__(self, index, value):
        self.setPixelColor(index, value)

    def __getitem__(self, index):
        return self._led_data[index]

# noinspection PyPep8Naming
def Color(red, green, blue, white=0):
    return (white << 24) | (red << 16) | (green << 8) | blue