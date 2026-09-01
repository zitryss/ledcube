import time
from random import uniform

from led_cube import NUM_LEDS, run


MAX_HUE = 50 / 360
MIN_BRIGHTNESS = 0.15
FRAME_INTERVAL_S = 0.08


def main(cube):
    while True:
        for index in range(NUM_LEDS):
            hue = uniform(0.0, MAX_HUE)
            brightness = uniform(MIN_BRIGHTNESS, 1.0)
            cube.set_hsv(index, hue, 1.0, brightness)
        time.sleep(FRAME_INTERVAL_S)


if __name__ == "__main__":
    run(main)
