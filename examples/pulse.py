import time
from math import pi, sin

from led_cube import run


HUE = 0.5
BRIGHTNESS = 0.8
STEP_RADIANS = pi / 60
FRAME_INTERVAL_S = 1 / 60


def main(cube):
    phase = 0.0
    while True:
        wave = (1.0 + sin(phase)) / 2.0
        cube.fill_hsv(HUE, 1.0, wave * BRIGHTNESS)
        phase = (phase + STEP_RADIANS) % (2 * pi)
        time.sleep(FRAME_INTERVAL_S)


if __name__ == "__main__":
    run(main)
