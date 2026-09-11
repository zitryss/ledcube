# AGENTS.md

## About

LED Cube is a production MicroPython application for a Raspberry Pi Pico W with a Pimoroni Plasma WS2812 LED cube. It connects to Wi-Fi, starts WebREPL from `boot.py`, renders air-quality data received over MQTT in `main.py`, and provides a small HTTP maintenance endpoint for over-the-air updates.

## Tech Stack

- Pimoroni MicroPython 1.27.0
- Raspberry Pi Pico W
- Pimoroni LED Plasma WS2812

## Project Structure

```text
.
├── .gitignore                 # Local development files and device secrets
├── AGENTS.md                  # Agent instructions
├── boot.py                    # Connects Wi-Fi and starts WebREPL before the app
├── main.py                    # Air-quality visualization and maintenance endpoint
├── examples/                  # LED demos and local configuration templates
├── webrepl_upload.py          # Host-side WebREPL file uploader
├── webrepl_reset.py           # Host-side WebREPL reset helper
└── lib/
    └── umqtt/
        └── simple.py          # MicroPython MQTT client
```

Device operation also depends on three local files: `WIFI_CONFIG.py`, `MQTT_CONFIG.py`, and `webrepl_cfg.py`, which are copied to or imported on the Pico. Safe templates for them live in `examples/`. `webrepl_cfg.py` is also the single password source for the host-side WebREPL helpers; it must define a non-empty `PASS` string.

## Control Model

`main.py` subscribes to three MQTT topics provided by Home Assistant and the MQTT broker:

- `airgradient/co2` supplies the latest CO₂ measurement.
- `airgradient/pm25` supplies the latest PM2.5 measurement.
- `led-cube/on` enables or disables visible LED output.

CO₂ and PM2.5 jointly determine the cube color. Preserve the threshold and color behavior when changing the visualization:

| State   | CO₂             | PM2.5          | LED behavior                          |
| ------- | --------------- | -------------- | ------------------------------------- |
| Good    | Below 700       | Below 50       | Green                                 |
| Warning | 700–999         | 50–149         | Orange transitioning toward red       |
| Bad     | 1000 or greater | 150 or greater | Red                                   |

The worst current measurement controls the warning color. A numeric `0` on `led-cube/on` makes the cube dark without discarding the latest sensor values; a numeric `1` restores their visualization. If no sensor update arrives for the configured idle interval, the cube displays its idle blue state, except while either sensor's unknown warning is active.

The literal MQTT payload `unknown` on either `airgradient/co2` or `airgradient/pm25` activates a precautionary red warning for that sensor. It does not represent a measured high concentration and must not replace the last numeric value with a fabricated reading. Only a valid, finite, non-negative reading from the same sensor clears its warning. Updates from the other sensor, invalid payloads, and the idle timeout do not clear it. If both sensors report `unknown`, both must recover before normal color calculation resumes. The on/off control still works, and maintenance mode still uses its dedicated color. These warnings are held in memory, not persisted across reboots. Other invalid payloads retain their existing ignore behavior.

## Key Constraints

- **MicroPython, not CPython:** Files copied to the Pico must remain compatible with its constrained MicroPython runtime and installed Pimoroni firmware modules. Do not require type annotations or use CPython-only syntax, standard-library modules, or APIs in device code.
- **`boot.py` owns Wi-Fi:** `boot.py` must activate the station interface, connect with `WIFI_CONFIG`, and start WebREPL. `main.py` only verifies that the shared station interface remains connected; if it is not, the existing reset path reboots the Pico so `boot.py` can retry. Do not add a second Wi-Fi manager or duplicate connection credentials in `main.py`.
- **Keep WebREPL reachable:** `boot.py` must establish Wi-Fi and start the firmware-provided WebREPL before `main.py` runs.
- **Foreground application must exit for OTA:** Enter maintenance mode before uploading files so the MQTT and LED loop stops and the REPL becomes available.
- **Maintenance must survive MQTT failure:** `main.py` must bind TCP/8267 before attempting MQTT connections and must continue polling the control socket while MQTT reconnects. Home Assistant or broker failure must not block OTA access.
- **No device package environment:** Device dependencies are MicroPython built-ins, firmware-provided Pimoroni modules, and `lib/umqtt/simple.py`. Host helpers may use a local virtual environment.
- **Keep host and device code distinct:** Host-side CPython helpers may use CPython features, but those features must not leak into files deployed to the Pico.
- **Keep one WebREPL password source:** Both the Pico firmware and the host-side WebREPL helpers read `PASS` from the local `webrepl_cfg.py`.

## Development Environments and Tooling Policy

The deployment destination is the boundary between the two Python environments:

- **Pico/device code:** Every file copied to the Raspberry Pi Pico must comply with MicroPython and the device constraints above. This includes `boot.py`, `main.py`, the entire `lib/` directory, `WIFI_CONFIG.py`, `MQTT_CONFIG.py`, `webrepl_cfg.py`, and any future uploaded file. Do not add CPython-only imports, APIs, syntax, or typing requirements merely to satisfy a desktop tool.
- **Host-only code:** Files that are never copied to the Pico, including `webrepl_upload.py`, `webrepl_reset.py`, and future development or automation helpers, are normal CPython applications. Develop them with modern CPython features, type annotations, and the tools installed in the project `.venv`; MicroPython limitations do not apply to them.

The project `.venv` provides `ruff`, `mypy`, `pyright`, `mpremote`, and the `websocket-client` distribution (imported as `websocket`). Prefer the executables in `.venv/bin/` over globally installed tools.

For every new or changed host-only Python file, use the available developer tools as applicable. In particular, run Ruff, mypy, and Pyright for host helpers such as the WebREPL uploader and reset utility; resolve their findings rather than weakening checks globally. When invoking Pyright directly, point it at the virtual-environment interpreter so it can resolve packages installed in `.venv`:

```bash
.venv/bin/ruff check webrepl_upload.py webrepl_reset.py
.venv/bin/mypy webrepl_upload.py webrepl_reset.py
.venv/bin/pyright --pythonpath .venv/bin/python webrepl_upload.py webrepl_reset.py
```

Use `.venv/bin/mpremote` for supported USB/serial device inspection or file operations when appropriate. Continue to use the project WebREPL helpers for the normal Wi-Fi OTA workflow; they may and should use `websocket-client` and other host-side packages from `.venv`.

Desktop syntax checks can still catch basic mistakes in device files, but passing Ruff, mypy, Pyright, or CPython compilation does not establish MicroPython compatibility. Review device code against the firmware/runtime limitations and verify behavior on the Pico.

## Normal Over-the-Air Update Pipeline

`webrepl_upload.py` is the project-specific WebREPL PUT client. It uses `websocket-client` to send normal masked WebSocket frames while speaking MicroPython's WebREPL file-transfer protocol. Use it instead of the stock WebREPL upload client for this device.

1. Edit the device files locally.
   Replace the documentation address `192.0.2.1` below with the cube's address.
2. Run a host-side syntax check:

   ```bash
   python3 -m py_compile main.py boot.py webrepl_upload.py webrepl_reset.py examples/MQTT_CONFIG.py examples/WIFI_CONFIG.py examples/webrepl_cfg.py lib/umqtt/simple.py
   ```

   This verifies Python syntax but does not prove MicroPython compatibility.

3. Confirm the application is running:

   ```bash
   curl -m 5 http://192.0.2.1:8267/status
   ```

   Expected response:

   ```text
   OK status app
   ```

4. Enter maintenance mode:

   ```bash
   curl -m 5 http://192.0.2.1:8267/maintenance/on
   ```

   Expected response:

   ```text
   OK maintenance on
   ```

5. Wait for `main.py` to close TCP/8267, disconnect MQTT, and return. The status endpoint becoming unreachable is expected and leaves the REPL available for WebREPL.
6. Upload the required files:

   ```bash
   . .venv/bin/activate
   python3 webrepl_upload.py --host 192.0.2.1 MQTT_CONFIG.py MQTT_CONFIG.py
   python3 webrepl_upload.py --host 192.0.2.1 main.py main.py
   ```

   Use the same uploader for any other changed device file. A successful upload prints the remote WebREPL version bytes and uploaded byte count.

7. Reboot the Pico through WebREPL:

   ```bash
   python3 webrepl_reset.py --host 192.0.2.1
   ```

8. Verify that the application and WebREPL returned:

   ```bash
   curl -m 5 http://192.0.2.1:8267/status
   nc -vz -G 3 192.0.2.1 8266
   ```

   Expected results:

   ```text
   OK status app
   Connection to 192.0.2.1 port 8266 succeeded
   ```

## Maintenance Endpoint Behavior

`main.py` listens on TCP/8267 while the LED Cube application is running.

- `/` or `/status` returns `OK status app`.
- `/maintenance/on`, `/maintenance`, or `/maint` returns `OK maintenance on`. The application changes the LEDs to the maintenance color, closes the control socket, disconnects MQTT, and exits.
- Every other path returns `ERR unknown path` with HTTP 404.

There is no maintenance-off endpoint. Reboot the Pico after upload to return to normal application mode. Wi-Fi and WebREPL remain available during maintenance because `boot.py` started them before the application.

## MicroPython

Apply the guidelines below when writing or reviewing the Pico/device files: `boot.py`, `main.py`, `lib/umqtt/__init__.py`, `lib/umqtt/simple.py`, and all `examples/*.py` files (the device demos, shared LED helper, and configuration templates). They also apply to the ignored local device configuration files `WIFI_CONFIG.py`, `MQTT_CONFIG.py`, and `webrepl_cfg.py`, and any future Python file intended to run on the Pico. Review these files under MicroPython guidelines, including `webrepl_cfg.py` even though host helpers also read it.

- Indent with 4 spaces, never tabs
- Follow PEP 8 style guide
- Prefer absolute imports over relative imports
- Avoid wildcard imports `from module import *`
- Import standard modules by their normal names, such as `time`, rather than legacy `u`-prefixed names such as `utime`
- Provide default arguments in functions where applicable
- Never use mutable objects as default function arguments
- Always use double-quoted strings (`"`) — never single-quoted (`'`)
- Always add a trailing comma after the last item in any multi-line collection, function definition, or function call
- Use list, dictionary, set, and generator comprehensions when it improves code readability
- Do not use stepped slicing; MicroPython does not support it consistently across built-in sequence types
- Use context managers `with` for file operations and resource management
- Do not rely on `__exit__()` being called for a context manager used inside a generator when the generator is abandoned before completion
- Do not rely on `__del__()` for resource cleanup; release resources explicitly
- Use plain path strings and the built-in `os` module for filesystem path-related operations
- Do not assume that either CPython's `os.path` or `pathlib` is present in the firmware
- Use `time.ticks_ms()` with `time.ticks_diff()` for elapsed time and intervals, and use `time.ticks_add()` with `time.ticks_diff()` for deadlines; use `time.time()` for absolute timestamps only when the device's RTC is set and maintained
- Never use bare `except:` statements
- Catch specific exceptions rather than broad try/except blocks
- Raise specific built-in or domain-specific exceptions rather than a generic `Exception`
- Catch `OSError` for filesystem, socket, and device I/O failures, and inspect `exc.errno` with constants from `errno`
- Do not rely on CPython `OSError` subclasses
- Catch `ValueError` when decoding malformed JSON; MicroPython does not provide `json.JSONDecodeError`
- Validate that values are JSON-compatible before serialization; MicroPython's `json.dumps()` may serialize `bytes` instead of raising `TypeError`
- Do not use `raise ... from exc`; MicroPython does not support exception chaining
- Never silently swallow a broad `except Exception`; report or recover from the failure explicitly and re-raise when appropriate
- Use `pytest` on the development computer for host-side tests
- Organize imports at the top of a file, followed by constants, then classes and functions, with `if __name__ == "__main__"` at the bottom

## Python

Apply the guidelines below when writing or reviewing the host-only CPython files: `webrepl_upload.py`, `webrepl_reset.py`, `tests/__init__.py`, and `tests/test_sensor_unknown.py`, plus future host-only tests and development or automation helpers. The tests run on the development computer, so these Python guidelines apply even when they test mocked device code. The MicroPython guidelines above apply to the device files; the Python guidelines below apply only to this host-only group.

- Indent with 4 spaces, never tabs
- Follow PEP 8 style guide
- ALWAYS apply type hints to ALL function and variables annotations
- Prefer absolute imports over relative imports
- Avoid wildcard imports `from module import *`
- Provide default arguments in functions where applicable
- Never use mutable objects as default function arguments
- Use f-strings for string formatting
- Always use double-quoted strings (`"`) — never single-quoted (`'`)
- Always add a trailing comma after the last item in any multi-line collection, function definition, or function call
- Use list, dictionary, set, and generator comprehensions when it improves code readability
- Use context managers `with` for file operations and resource management
- Use `pathlib` instead of `os.path` for filesystem path-related operations
- Use logging instead of print statements for errors and debugging
- Never use bare `except:` statements
- Catch specific exceptions rather than broad try/except blocks
- Use `pytest` for testing
- Use `dataclass` for data containers
- Organize imports at the top of a file, followed by constants, then classes and functions, with `if __name__ == "__main__"` at the bottom
- Use PEP 585 built-in generics such as `list[int]` and `dict[str, float]` instead of their `typing` equivalents
- Use concrete type annotations; reserve `Any` for cases where an unconstrained type is truly needed
- Use a named logger created with `logging.getLogger(__name__)` for each module instead of calling the root logger directly; `print()` is acceptable for intentional command-line output
- For logging messages, pass values as logging arguments with %-style placeholders or through `extra` instead of using f-strings
- Raise specific built-in or domain-specific exceptions rather than a generic `Exception`
- If a broad exception catch is necessary, re-raise the exception or preserve its traceback with `logger.exception()` or `exc_info=True`; never silently swallow it
