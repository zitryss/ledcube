import time
from random import choice, random

from led_cube import NUM_LEDS, run


TREE_COLOR = (0.34, 1.0, 0.45)
LIGHT_COLORS = (
    (0.0, 1.0, 0.8),
    (0.1, 1.0, 0.8),
    (0.6, 1.0, 0.8),
    (0.85, 0.4, 0.8),
)
LIGHT_SPACING = 8
LIGHT_CHANGE_CHANCE = 0.5
UPDATE_INTERVAL_S = 0.5


def main(cube):
    for index in range(NUM_LEDS):
        color = choice(LIGHT_COLORS) if index % LIGHT_SPACING == 0 else TREE_COLOR
        cube.set_hsv(index, *color)

    while True:
        for index in range(0, NUM_LEDS, LIGHT_SPACING):
            if random() < LIGHT_CHANGE_CHANCE:
                cube.set_hsv(index, *choice(LIGHT_COLORS))
        time.sleep(UPDATE_INTERVAL_S)


if __name__ == "__main__":
    run(main)
