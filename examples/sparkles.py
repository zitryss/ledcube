import time
from random import random

from led_cube import NUM_LEDS, run


BACKGROUND = (35, 35, 0)
SPARKLE = (255, 255, 80)
SPARKLE_CHANCE = 0.01
FADE_UP_PER_FRAME = 24
FADE_DOWN_PER_FRAME = 4
FRAME_INTERVAL_S = 0.02


def approach(current, target):
    if current < target:
        return min(current + FADE_UP_PER_FRAME, target)
    if current > target:
        return max(current - FADE_DOWN_PER_FRAME, target)
    return current


def main(cube):
    colors = [list(BACKGROUND) for _ in range(NUM_LEDS)]
    targets = [BACKGROUND for _ in range(NUM_LEDS)]

    while True:
        for index in range(NUM_LEDS):
            if random() < SPARKLE_CHANCE:
                targets[index] = SPARKLE
            elif tuple(colors[index]) == SPARKLE:
                targets[index] = BACKGROUND

            colors[index] = [
                approach(colors[index][channel], targets[index][channel])
                for channel in range(3)
            ]
            cube.set_rgb(index, *colors[index])
        time.sleep(FRAME_INTERVAL_S)


if __name__ == "__main__":
    run(main)
