import plasma


NUM_LEDS = 50
DATA_PIN = 15


def clamp(value, minimum=0.0, maximum=1.0):
    return min(maximum, max(minimum, value))


def scale(value, input_minimum, input_maximum, output_minimum, output_maximum):
    if input_maximum == input_minimum:
        raise ValueError("input range must not be empty")

    position = (value - input_minimum) / (input_maximum - input_minimum)
    position = clamp(position)
    return output_minimum + position * (output_maximum - output_minimum)


def hsv_to_rgb(hue, saturation, value):
    hue = hue % 1.0
    saturation = clamp(saturation)
    value = clamp(value)
    if saturation == 0.0:
        channel = int(value * 255)
        return (channel, channel, channel)

    sector = int(hue * 6.0)
    fraction = hue * 6.0 - sector
    low = value * (1.0 - saturation)
    falling = value * (1.0 - saturation * fraction)
    rising = value * (1.0 - saturation * (1.0 - fraction))
    combinations = (
        (value, rising, low),
        (falling, value, low),
        (low, value, rising),
        (low, falling, value),
        (rising, low, value),
        (value, low, falling),
    )
    return tuple(int(channel * 255) for channel in combinations[sector % 6])


class LedCube:
    def __init__(self):
        self.strip = plasma.WS2812(
            NUM_LEDS,
            0,
            0,
            DATA_PIN,
            color_order=plasma.COLOR_ORDER_RGB,
        )
        self.strip.start()

    def set_hsv(self, index, hue, saturation, brightness):
        self.strip.set_hsv(
            index,
            hue % 1.0,
            clamp(saturation),
            clamp(brightness),
        )

    def set_rgb(self, index, red, green, blue):
        self.strip.set_rgb(
            index,
            int(clamp(red, 0, 255)),
            int(clamp(green, 0, 255)),
            int(clamp(blue, 0, 255)),
        )

    def fill_hsv(self, hue, saturation, brightness):
        for index in range(NUM_LEDS):
            self.set_hsv(index, hue, saturation, brightness)

    def fill_rgb(self, red, green, blue):
        for index in range(NUM_LEDS):
            self.set_rgb(index, red, green, blue)

    def clear(self):
        self.fill_rgb(0, 0, 0)


def run(example):
    cube = LedCube()
    try:
        example(cube)
    except KeyboardInterrupt:
        pass
    finally:
        cube.clear()
