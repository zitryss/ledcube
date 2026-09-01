# LED Cube examples

These examples preserve the ideas from the demo files that were previously stored
on the Pico. They are rewritten for this project's 50-LED cube on GP15 and are not
part of the production application.

Run an example from the repository without copying it permanently to the Pico:

```bash
.venv/bin/mpremote connect auto mount examples run examples/fire.py
```

Press `Ctrl-C` to stop an example. Reset the Pico afterward to restart `boot.py`
and `main.py`:

```bash
.venv/bin/mpremote connect auto reset
```

The MQTT and weather examples rely on the Wi-Fi connection established by
`boot.py`; they do not manage Wi-Fi themselves. Edit the location constants in
`weather.py` before use. None of the examples require external sensors, breakout
boards, or other additional hardware.

Examples are intentionally kept off the Pico's persistent filesystem so only the
production LED Cube application starts after a reboot.
