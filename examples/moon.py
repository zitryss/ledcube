import time
from machine import RTC

from led_cube import run, scale


HUE = 60 / 360
SATURATION = 0.2
GLOW_WINDOW_S = 4 * 60 * 60
UPDATE_INTERVAL_S = 10


def seconds_from_midnight(datetime):
    hour = datetime[4]
    minute = datetime[5]
    second = datetime[6]
    return hour * 3600 + minute * 60 + second


def midnight_brightness(datetime):
    elapsed = seconds_from_midnight(datetime)
    distance = min(elapsed, 24 * 60 * 60 - elapsed)
    return scale(distance, 0, GLOW_WINDOW_S, 1.0, 0.0)


def main(cube):
    rtc = RTC()
    while True:
        now = rtc.datetime()
        brightness = midnight_brightness(now)
        cube.fill_hsv(HUE, SATURATION, brightness)
        print("RTC:", now, "moon brightness:", brightness)
        time.sleep(UPDATE_INTERVAL_S)


if __name__ == "__main__":
    run(main)
