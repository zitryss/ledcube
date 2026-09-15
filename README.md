# LED Cube

An ambient air-quality display that turns CO₂ and PM2.5 readings from an AirGradient monitor into a room-readable green-to-red signal.

Built with a Raspberry Pi Pico W, a 50-LED Pimoroni Plasma cube, and MicroPython.

## From the air to the LEDs

The AirGradient monitor is integrated with Home Assistant, which publishes its readings as MQTT messages. The Pico W subscribes to those messages and turns them into colors on the cube.

```mermaid
flowchart LR
    air["AirGradient<br/>Measures the air"] --> ha["Home Assistant<br/>Publishes readings"]
    ha -->|MQTT| pico["Pico W<br/>Runs MicroPython"]
    pico --> cube["LED Cube<br/>Colors the room"]

    classDef coral fill:#ffdfd5,stroke:#ae4930,color:#492117,stroke-width:2px;
    classDef violet fill:#e9dfff,stroke:#7951b0,color:#35204f,stroke-width:2px;
    classDef blue fill:#d9edff,stroke:#3975ac,color:#153b5a,stroke-width:2px;
    classDef mint fill:#d2f6e8,stroke:#287e64,color:#123f30,stroke-width:2px;
    class air coral;
    class ha violet;
    class pico blue;
    class cube mint;
```

## Open the hood

### What happens when MQTT is unavailable?

The cube needs MQTT for new readings and on/off commands. Its HTTP maintenance endpoint stays reachable while MQTT reconnects, provided the Pico remains connected to Wi-Fi. Access for fixing the app does not depend on the broker working.

### Updates over Wi-Fi

Enter maintenance mode to pause the app for uploads through WebREPL. Wi-Fi and WebREPL start before the application; maintenance mode stops the LED and MQTT loop and leaves the REPL available. Reboot the Pico after uploading to resume normal operation.

A custom upload client handles the Pico firmware's WebSocket requirements.

<img src="https://github.com/user-attachments/assets/54186bad-292d-4bf9-b413-2c99e84c3d1c" alt="LED cube visualizing AirGradient air-quality readings" width="360">
