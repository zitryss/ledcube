# LED Cube

An ambient air-quality display that turns CO₂ and PM2.5 readings from an AirGradient monitor into a room-readable green-to-red signal.

Built with a Raspberry Pi Pico W, a 50-LED Pimoroni Plasma cube, and MicroPython.

The AirGradient monitor is integrated with Home Assistant, which publishes its readings as MQTT messages. The cube subscribes to those messages and provides a second, glanceable display of the same values.

**Updates over Wi-Fi.** A maintenance endpoint remains reachable during MQTT failures and pauses the app for uploads through WebREPL. A custom client handles the Pico firmware's WebSocket requirements.

<img src="https://github.com/user-attachments/assets/54186bad-292d-4bf9-b413-2c99e84c3d1c" alt="LED cube visualizing AirGradient air-quality readings" width="360">
