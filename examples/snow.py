import time
from random import random

from led_cube import NUM_LEDS, run


BACKGROUND = (20, 35, 45)
SNOWFLAKE = (230, 245, 255)
SNOWFLAKE_CHANCE = 0.004
FADE_PER_FRAME = 3
FRAME_INTERVAL_S = 0.02


def approach(current, target):
    if current < target:
        return min(current + FADE_PER_FRAME, target)
    if current > target:
        return max(current - FADE_PER_FRAME, target)
    return current


def main(cube):
    colors = [list(BACKGROUND) for _ in range(NUM_LEDS)]
    targets = [BACKGROUND for _ in range(NUM_LEDS)]

    while True:
        for index in range(NUM_LEDS):
            if random() < SNOWFLAKE_CHANCE:
                colors[index] = list(SNOWFLAKE)
                targets[index] = BACKGROUND

            colors[index] = [
                approach(colors[index][channel], targets[index][channel])
                for channel in range(3)
            ]
            cube.set_rgb(index, *colors[index])
        time.sleep(FRAME_INTERVAL_S)


if __name__ == "__main__":
    run(main)
