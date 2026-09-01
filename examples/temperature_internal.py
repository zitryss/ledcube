import time
from machine import ADC

from led_cube import run, scale


MIN_TEMPERATURE_C = 10
MAX_TEMPERATURE_C = 30
BLUE_HUE = 230 / 360
RED_HUE = 359 / 360
BRIGHTNESS = 0.6
SAMPLE_COUNT = 10
SAMPLE_INTERVAL_S = 0.5


def read_temperature(sensor):
    voltage = sensor.read_u16() * 3.3 / 65535
    return 27 - (voltage - 0.706) / 0.001721


def main(cube):
    sensor = ADC(4)
    samples = [20.0] * SAMPLE_COUNT
    next_sample = 0

    while True:
        samples[next_sample] = read_temperature(sensor)
        next_sample = (next_sample + 1) % SAMPLE_COUNT
        average = sum(samples) / len(samples)
        hue = scale(
            average,
            MIN_TEMPERATURE_C,
            MAX_TEMPERATURE_C,
            BLUE_HUE,
            RED_HUE,
        )
        cube.fill_hsv(hue, 1.0, BRIGHTNESS)
        print("Average internal temperature:", average, "C")
        time.sleep(SAMPLE_INTERVAL_S)


if __name__ == "__main__":
    run(main)
