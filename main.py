"""Air-quality LED cube application for Pimoroni MicroPython."""

import errno
import machine
import network
import socket
import time

import plasma
from umqtt.simple import MQTTClient, MQTTException

try:
    import MQTT_CONFIG
except (ImportError, SyntaxError) as exc:
    print("MQTT_CONFIG.py could not be loaded:", exc)
    MQTT_CONFIG = None

MQTT_CLIENT_ID = "pico-plasma"
MQTT_KEEPALIVE = 60
MQTT_TOPIC_CO2 = b"airgradient/co2"
MQTT_TOPIC_PM25 = b"airgradient/pm25"
MQTT_TOPIC_ON = b"led-cube/on"
MQTT_PING_INTERVAL_MS = 63_000
MQTT_RECONNECT_INTERVAL_MS = 5_000
MQTT_IDLE_COLOR_INTERVAL_MS = 130_000
MQTT_SOCKET_TIMEOUT_S = 5

CONTROL_PORT = 8267
CONTROL_REQUEST_MAX_BYTES = 1024
PLASMA_NUM_LEDS = 50
PLASMA_DATA_PIN = 15
PLASMA_SATURATION = 1.0
DEFAULT_BRIGHTNESS = 0.6
MAINTENANCE_HUE = 0.78
MAINTENANCE_BRIGHTNESS = 0.25

CO2_GOOD = 700
CO2_BAD = 1000
PM25_GOOD = 50
PM25_BAD = 150


def report_os_error(message, exc):
    print(message, "(errno", exc.errno, "):", exc)


class LedCube:
    """Own the cube state, air-quality rules, and LED rendering."""

    def __init__(self):
        self._strip = plasma.WS2812(
            PLASMA_NUM_LEDS,
            0,
            0,
            PLASMA_DATA_PIN,
            color_order=plasma.COLOR_ORDER_RGB,
        )
        self._strip.start()

        self._co2 = 0
        self._pm25 = 0
        self._co2_unknown = False
        self._pm25_unknown = False
        self._is_enabled = True
        self._last_sensor_update_ms = time.ticks_ms()
        self._is_showing_idle = False

    def update_co2(self, value):
        self._co2 = value
        self._co2_unknown = False
        self._sensor_updated()

    def update_pm25(self, value):
        self._pm25 = value
        self._pm25_unknown = False
        self._sensor_updated()

    def mark_co2_unknown(self):
        # Missing CO2 warrants a warning without inventing a concentration.
        self._co2_unknown = True
        self._sensor_updated()

    def mark_pm25_unknown(self):
        # Missing PM2.5 warrants a warning without inventing a concentration.
        self._pm25_unknown = True
        self._sensor_updated()

    def set_enabled(self, is_enabled):
        self._is_enabled = bool(is_enabled)
        self._is_showing_idle = False
        self._render_air_quality()

    def show_idle_if_due(self):
        # Each unknown warning needs a valid reading from that same sensor.
        if self._is_showing_idle or self._co2_unknown or self._pm25_unknown:
            return
        elapsed_ms = time.ticks_diff(
            time.ticks_ms(),
            self._last_sensor_update_ms,
        )
        if elapsed_ms < MQTT_IDLE_COLOR_INTERVAL_MS:
            return

        self._show_color(240 / 360, DEFAULT_BRIGHTNESS)
        self._is_showing_idle = True

    def show_maintenance(self):
        self._set_all_leds(
            MAINTENANCE_HUE,
            PLASMA_SATURATION,
            MAINTENANCE_BRIGHTNESS,
        )

    def show_error(self):
        self._set_all_leds(0, 0, 1.0)

    def _sensor_updated(self):
        self._last_sensor_update_ms = time.ticks_ms()
        self._is_showing_idle = False
        self._render_air_quality()

    def _render_air_quality(self):
        hue, brightness = self._air_quality_color()
        self._show_color(hue, brightness)

    def _air_quality_color(self):
        if (
            self._co2_unknown
            or self._pm25_unknown
            or self._co2 >= CO2_BAD
            or self._pm25 >= PM25_BAD
        ):
            return (0, DEFAULT_BRIGHTNESS)

        co2_warning = self._co2 >= CO2_GOOD
        pm25_warning = self._pm25 >= PM25_GOOD
        if co2_warning or pm25_warning:
            worst_position = max(
                (self._co2 - CO2_GOOD) / (CO2_BAD - CO2_GOOD)
                if co2_warning
                else 0,
                (self._pm25 - PM25_GOOD) / (PM25_BAD - PM25_GOOD)
                if pm25_warning
                else 0,
            )
            hue_degrees = 33 - worst_position * 33
            return (hue_degrees / 360, DEFAULT_BRIGHTNESS)

        return (100 / 360, 0.4)

    def _show_color(self, hue, brightness):
        brightness_factor = 1 if self._is_enabled else 0
        self._set_all_leds(
            hue,
            PLASMA_SATURATION,
            brightness * brightness_factor,
        )

    def _set_all_leds(self, hue, saturation, brightness):
        for index in range(PLASMA_NUM_LEDS):
            self._strip.set_hsv(index, hue, saturation, brightness)


class MqttConnection:
    """Own MQTT connection state, subscriptions, and message handling."""

    def __init__(self, led_cube, mqtt_config):
        self._led_cube = led_cube
        self._server = None
        self._port = None
        self._user = None
        self._password = None
        if mqtt_config is not None:
            server = getattr(mqtt_config, "MQTT_SERVER", None)
            port = getattr(mqtt_config, "MQTT_PORT", None)
            user = getattr(mqtt_config, "MQTT_USER", None)
            password = getattr(mqtt_config, "MQTT_PASSWORD", None)
            if isinstance(server, str) and server:
                self._server = server
            if (
                not isinstance(port, bool)
                and isinstance(port, int)
                and 1 <= port <= 65535
            ):
                self._port = port
            if isinstance(user, str) and user:
                self._user = user
            if isinstance(password, str) and password:
                self._password = password
        self._client = None
        self._last_connect_attempt_ms = None
        self._last_ping_ms = 0
        self._configuration_error_reported = False

    def poll(self):
        now_ms = time.ticks_ms()
        if self._client is None:
            self._connect_if_due(now_ms)
        if self._client is None:
            return

        try:
            self._client.check_msg()
            if (
                time.ticks_diff(now_ms, self._last_ping_ms)
                >= MQTT_PING_INTERVAL_MS
            ):
                self._client.ping()
                self._last_ping_ms = now_ms
        # Partial reads in the bundled non-blocking client can surface as
        # indexing errors instead of OSError.
        except (OSError, MQTTException, AssertionError, IndexError, TypeError) as exc:
            print("mqtt loop failed:", exc)
            self.close()

    def close(self):
        client = self._client
        self._client = None
        self._close_client(client)

    def _connect_if_due(self, now_ms):
        if (
            self._last_connect_attempt_ms is not None
            and time.ticks_diff(now_ms, self._last_connect_attempt_ms)
            < MQTT_RECONNECT_INTERVAL_MS
        ):
            return

        self._last_connect_attempt_ms = now_ms
        if (
            self._server is None
            or self._port is None
            or self._user is None
            or self._password is None
        ):
            if not self._configuration_error_reported:
                print("MQTT_CONFIG.py contains missing or invalid broker settings")
                self._configuration_error_reported = True
            return

        client = None
        try:
            print("connecting to mqtt...")
            client = MQTTClient(
                MQTT_CLIENT_ID,
                self._server,
                port=self._port,
                user=self._user,
                password=self._password,
                keepalive=MQTT_KEEPALIVE,
                socket_timeout=MQTT_SOCKET_TIMEOUT_S,
            )
            client.set_callback(self._handle_message)
            client.connect()
            client.subscribe(MQTT_TOPIC_CO2)
            client.subscribe(MQTT_TOPIC_PM25)
            client.subscribe(MQTT_TOPIC_ON)

            self._client = client
            self._last_ping_ms = now_ms
            print("mqtt connected")
        except (OSError, MQTTException, AssertionError, IndexError, TypeError) as exc:
            print("mqtt connect failed:", exc)
            self._close_client(client)

    def _handle_message(self, topic, message):
        print("topic: " + str(topic), "msg: " + str(message))

        if topic == MQTT_TOPIC_CO2:
            if message == b"unknown":
                self._led_cube.mark_co2_unknown()
                return
            value = self._parse_measurement(message)
            if value is not None:
                self._led_cube.update_co2(value)
            return

        if topic == MQTT_TOPIC_PM25:
            if message == b"unknown":
                self._led_cube.mark_pm25_unknown()
                return
            value = self._parse_measurement(message)
            if value is not None:
                self._led_cube.update_pm25(value)
            return

        if topic == MQTT_TOPIC_ON:
            is_enabled = self._parse_enabled(message)
            if is_enabled is not None:
                self._led_cube.set_enabled(is_enabled)

    def _parse_measurement(self, message):
        try:
            value = float(message)
        except (ValueError, TypeError):
            print("ignoring non-numeric air quality payload:", message)
            return None

        if not 0 <= value < float("inf"):
            print("ignoring invalid air quality payload:", message)
            return None
        return value

    def _parse_enabled(self, message):
        try:
            value = int(message)
        except (ValueError, TypeError):
            print("ignoring non-numeric led-cube/on payload:", message)
            return None

        if value not in (0, 1):
            print("ignoring invalid led-cube/on payload:", message)
            return None
        return value == 1

    def _close_client(self, client):
        if client is None:
            return

        client_socket = getattr(client, "sock", None)
        if client_socket is None:
            return

        try:
            client.disconnect()
        except OSError as exc:
            report_os_error("mqtt disconnect failed", exc)
        else:
            return

        try:
            client_socket.close()
        except OSError as exc:
            report_os_error("mqtt socket close failed", exc)


class ControlServer:
    """Non-blocking HTTP endpoint for status and OTA maintenance."""

    def __init__(self, port):
        self._port = port
        self._socket = None

    def open(self):
        if self._socket is not None:
            return

        control = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            control.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            control.bind(("0.0.0.0", self._port))
            control.listen(1)
            control.setblocking(False)
            self._socket = control
        except OSError as exc:
            report_os_error("control server could not be opened", exc)
            try:
                control.close()
            except OSError as close_exc:
                report_os_error("control socket cleanup failed", close_exc)
            raise

    def close(self):
        control = self._socket
        self._socket = None
        if control is None:
            return
        try:
            control.close()
        except OSError as exc:
            report_os_error("control server close failed", exc)

    def poll_for_maintenance(self):
        if self._socket is None:
            raise RuntimeError("control server is not open")

        try:
            client, _address = self._socket.accept()
        except OSError as exc:
            if exc.errno == errno.EAGAIN:
                return False
            raise

        try:
            client.settimeout(1)
            data = client.recv(CONTROL_REQUEST_MAX_BYTES)
            path = self._request_path(data)
            maintenance, status, body = self._route(path)
            self._send_all(client, self._http_response(status, body))
            return maintenance
        except OSError as exc:
            report_os_error("control request failed", exc)
            return False
        finally:
            try:
                client.close()
            except OSError as exc:
                report_os_error("control client close failed", exc)

    def _request_path(self, data):
        try:
            request = data.decode()
        except UnicodeError:
            return ""

        first_line = request.split("\r\n", 1)[0]
        parts = first_line.split(" ")
        if len(parts) < 2 or not parts[1].startswith("/"):
            return ""
        return parts[1].lower()

    def _route(self, path):
        if path in ("/", "/status"):
            return (False, "200 OK", "OK status app\n")
        if path in ("/maintenance/on", "/maint", "/maintenance"):
            return (True, "200 OK", "OK maintenance on\n")
        return (False, "404 Not Found", "ERR unknown path\n")

    def _http_response(self, status, body):
        payload = body.encode()
        headers = (
            "HTTP/1.1 " + status + "\r\n"
            "Content-Type: text/plain\r\n"
            "Content-Length: " + str(len(payload)) + "\r\n"
            "Connection: close\r\n"
            "\r\n"
        )
        return headers.encode() + payload

    def _send_all(self, client, data):
        total_sent = 0
        while total_sent < len(data):
            sent = client.send(data[total_sent:])
            if not sent:
                raise OSError(errno.EIO, "socket send returned 0")
            total_sent += sent


class LedCubeApplication:
    """Coordinate the cube, MQTT connection, and maintenance endpoint."""

    def __init__(self, led_cube, mqtt_connection, control_server):
        self._led_cube = led_cube
        self._mqtt_connection = mqtt_connection
        self._control_server = control_server

    def run(self):
        self._verify_wifi_connected()
        print("starting control endpoint...")
        self._control_server.open()

        try:
            while True:
                if self._control_server.poll_for_maintenance():
                    self._led_cube.show_maintenance()
                    print("maintenance requested; exiting to REPL")
                    return

                self._mqtt_connection.poll()
                self._led_cube.show_idle_if_due()
                time.sleep_ms(100)
        finally:
            try:
                self._control_server.close()
            finally:
                self._mqtt_connection.close()

    def _verify_wifi_connected(self):
        wlan = network.WLAN(network.STA_IF)
        if wlan.active() and wlan.isconnected():
            return
        raise OSError("WiFi is not connected after boot")


def main():
    led_cube = LedCube()
    mqtt_connection = MqttConnection(led_cube, MQTT_CONFIG)
    control_server = ControlServer(CONTROL_PORT)
    application = LedCubeApplication(led_cube, mqtt_connection, control_server)

    try:
        application.run()
    except OSError as exc:
        print("error: " + str(exc))
        print("resetting...")
        led_cube.show_error()
        time.sleep(5)
        machine.reset()


if __name__ == "__main__":
    main()
