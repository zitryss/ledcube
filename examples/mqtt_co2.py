import network
import time

from umqtt.simple import MQTTClient

import MQTT_CONFIG
from led_cube import run, scale


MQTT_CLIENT_ID = b"pico-plasma-example"
MQTT_TOPIC = b"airgradient/co2"
MQTT_KEEPALIVE_S = 60
MQTT_PING_INTERVAL_S = 55

CO2_GOOD = 700
CO2_BAD = 1000
BRIGHTNESS = 0.6


def require_wifi():
    wlan = network.WLAN(network.STA_IF)
    if not wlan.active() or not wlan.isconnected():
        raise OSError("Wi-Fi is not connected; let boot.py connect first")


def show_co2(cube, payload):
    try:
        co2 = float(payload)
    except (TypeError, ValueError):
        print("Ignoring non-numeric CO2 payload:", payload)
        return

    if co2 < CO2_GOOD:
        hue = 100 / 360
        brightness = 0.4
    elif co2 >= CO2_BAD:
        hue = 0.0
        brightness = BRIGHTNESS
    else:
        hue = scale(co2, CO2_GOOD, CO2_BAD, 33 / 360, 0.0)
        brightness = BRIGHTNESS

    print("CO2:", co2, "hue:", hue)
    cube.fill_hsv(hue, 1.0, brightness)


def main(cube):
    require_wifi()
    user = MQTT_CONFIG.MQTT_USER.encode()
    password = MQTT_CONFIG.MQTT_PASSWORD.encode()
    client = MQTTClient(
        MQTT_CLIENT_ID,
        MQTT_CONFIG.MQTT_SERVER,
        port=MQTT_CONFIG.MQTT_PORT,
        user=user,
        password=password,
        keepalive=MQTT_KEEPALIVE_S,
    )
    client.set_callback(lambda topic, payload: show_co2(cube, payload))

    try:
        client.connect()
        client.subscribe(MQTT_TOPIC)
        last_ping = time.time()
        while True:
            client.check_msg()
            now = time.time()
            if now - last_ping >= MQTT_PING_INTERVAL_S:
                client.ping()
                last_ping = now
            time.sleep(0.1)
    finally:
        try:
            client.disconnect()
        except Exception:
            pass


if __name__ == "__main__":
    run(main)
