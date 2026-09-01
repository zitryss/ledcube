import network
import time
from random import randint, random

import urequests

from led_cube import NUM_LEDS, run


LATITUDE = 53.3861
LONGITUDE = -1.4240
UPDATE_INTERVAL_MS = 15 * 60 * 1000
FRAME_INTERVAL_S = 0.08

WEATHER_URL = (
    "https://api.open-meteo.com/v1/forecast"
    "?latitude=" + str(LATITUDE)
    + "&longitude=" + str(LONGITUDE)
    + "&current_weather=true&timezone=auto"
)


def require_wifi():
    wlan = network.WLAN(network.STA_IF)
    if not wlan.active() or not wlan.isconnected():
        raise OSError("Wi-Fi is not connected; let boot.py connect first")


def fetch_weather_code():
    response = None
    try:
        response = urequests.get(WEATHER_URL)
        if response.status_code != 200:
            raise OSError("weather request returned " + str(response.status_code))
        current_weather = response.json().get("current_weather")
        if not current_weather or "weathercode" not in current_weather:
            raise ValueError("weather response has no current weather code")
        code = int(current_weather["weathercode"])
        print("Weather code:", code)
        return code
    finally:
        if response:
            response.close()


def render_clear(cube, code):
    for index in range(NUM_LEDS):
        if code == 0:
            cube.set_rgb(index, randint(220, 255), randint(200, 240), randint(40, 90))
        else:
            cube.set_rgb(index, randint(10, 50), randint(130, 180), randint(170, 220))


def render_clouds(cube, code):
    base = 175 if code in (45, 48) else 130 if code == 2 else 85
    for index in range(NUM_LEDS):
        shade = max(0, min(255, base + randint(-20, 20)))
        cube.set_rgb(index, shade, shade, int(shade * 0.9))


def render_rain(cube, heavy=False):
    drop_chance = 0.25 if heavy else 0.08
    for index in range(NUM_LEDS):
        if random() < drop_chance:
            cube.set_rgb(index, randint(0, 50), randint(50, 130), randint(130, 255))
        else:
            cube.set_rgb(index, 0, 12, 45)


def render_snow(cube):
    for index in range(NUM_LEDS):
        brightness = 235 if random() < 0.12 else 50
        cube.set_rgb(index, brightness, brightness, min(255, brightness + 15))


def render_weather(cube, code):
    if code in (0, 1):
        render_clear(cube, code)
    elif 2 <= code <= 48:
        render_clouds(cube, code)
    elif 51 <= code <= 67 or 80 <= code <= 82:
        render_rain(cube, heavy=code in (65, 67, 82))
    elif 71 <= code <= 77 or 85 <= code <= 86:
        render_snow(cube)
    elif 95 <= code <= 99:
        if random() < 0.04:
            cube.fill_rgb(255, 255, 255)
        else:
            render_rain(cube, heavy=True)
    else:
        cube.fill_hsv(0.8, 1.0, 0.25)


def main(cube):
    require_wifi()
    weather_code = None
    last_update = None

    while True:
        now = time.ticks_ms()
        update_due = last_update is None or time.ticks_diff(now, last_update) >= UPDATE_INTERVAL_MS
        if update_due:
            try:
                weather_code = fetch_weather_code()
                last_update = now
            except Exception as exc:
                print("Weather update failed:", exc)
                if weather_code is None:
                    weather_code = 3
                last_update = now

        render_weather(cube, weather_code)
        time.sleep(FRAME_INTERVAL_S)


if __name__ == "__main__":
    run(main)
