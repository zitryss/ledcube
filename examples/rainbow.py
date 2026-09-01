import time

from led_cube import NUM_LEDS, run


BRIGHTNESS = 0.6
SPEED = 20
UPDATES_PER_SECOND = 60


def main(cube):
    offset = 0.0
    step = min(255, max(1, SPEED)) / 2000
    while True:
        offset = (offset + step) % 1.0
        for index in range(NUM_LEDS):
            cube.set_hsv(index, index / NUM_LEDS + offset, 1.0, BRIGHTNESS)
        time.sleep(1 / UPDATES_PER_SECOND)


if __name__ == "__main__":
    run(main)
