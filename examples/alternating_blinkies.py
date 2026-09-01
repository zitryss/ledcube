import time

from led_cube import NUM_LEDS, run


FIRST_HUE = 40 / 360
SECOND_HUE = 285 / 360
BRIGHTNESS = 0.5
INTERVAL_S = 1


def show_pair(cube, swap):
    for index in range(NUM_LEDS):
        use_first = (index % 2 == 0) != swap
        hue = FIRST_HUE if use_first else SECOND_HUE
        cube.set_hsv(index, hue, 1.0, BRIGHTNESS)


def main(cube):
    swap = False
    while True:
        show_pair(cube, swap)
        swap = not swap
        time.sleep(INTERVAL_S)


if __name__ == "__main__":
    run(main)
