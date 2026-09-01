"""Exercise MQTT payloads against the real cube logic without device hardware."""

import runpy
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from types import ModuleType
from typing import Protocol, cast

import pytest


class Cube(Protocol):
    def show_idle_if_due(self) -> None: ...

    def show_maintenance(self) -> None: ...


class Subscriber(Protocol):
    def _handle_message(self, topic: bytes, message: bytes) -> None: ...


@dataclass
class Clock:
    now: int = 0

    def ticks_ms(self) -> int:
        return self.now


@dataclass
class Strip:
    colors: dict[int, tuple[float, float, float]] = field(default_factory=dict)

    def start(self) -> None:
        pass

    def set_hsv(
        self,
        index: int,
        hue: float,
        saturation: float,
        brightness: float,
    ) -> None:
        self.colors[index] = (hue, saturation, brightness)


@dataclass
class Harness:
    cube: Cube
    send: Callable[[bytes, bytes], None]
    clock: Clock
    strip: Strip

    def expect_color(self, hue: float, brightness: float = 0.6) -> None:
        assert self.strip.colors == dict.fromkeys(range(50), (hue, 1.0, brightness))


@pytest.fixture
def app(monkeypatch: pytest.MonkeyPatch) -> Harness:
    clock = Clock()
    strip = Strip()
    plasma = ModuleType("plasma")
    plasma.__dict__.update(
        WS2812=lambda *_args, **_kwargs: strip,
        COLOR_ORDER_RGB=0,
    )
    mqtt_module = ModuleType("umqtt.simple")
    mqtt_module.__dict__.update(MQTTClient=object, MQTTException=OSError)
    for name in ("machine", "network", "MQTT_CONFIG", "umqtt"):
        monkeypatch.setitem(sys.modules, name, ModuleType(name))
    monkeypatch.setitem(sys.modules, "plasma", plasma)
    monkeypatch.setitem(sys.modules, "umqtt.simple", mqtt_module)
    monkeypatch.setattr(time, "ticks_ms", clock.ticks_ms, raising=False)
    monkeypatch.setattr(time, "ticks_diff", lambda now, then: now - then, raising=False)
    namespace = runpy.run_path(str(Path(__file__).resolve().parents[1] / "main.py"))
    cube = cast("Callable[[], Cube]", namespace["LedCube"])()
    subscriber = cast(
        "Callable[[Cube, None], Subscriber]",
        namespace["MqttConnection"],
    )(cube, None)
    # Exercise the callback used by MQTT without connecting to a real broker.
    return Harness(
        cube,
        subscriber._handle_message,  # noqa: SLF001
        clock,
        strip,
    )


@pytest.fixture(
    params=[
        (b"airgradient/co2", b"airgradient/pm25"),
        (b"airgradient/pm25", b"airgradient/co2"),
    ],
    ids=["co2", "pm25"],
)
def sensor_topics(request: pytest.FixtureRequest) -> tuple[bytes, bytes]:
    return cast("tuple[bytes, bytes]", request.param)


def test_unknown_turns_warning_red_and_survives_other_sensor_and_idle(
    app: Harness,
    sensor_topics: tuple[bytes, bytes],
) -> None:
    topic, other_topic = sensor_topics
    app.send(b"airgradient/co2", b"850")
    app.send(b"airgradient/pm25", b"100")
    app.expect_color(16.5 / 360)

    app.send(topic, b"unknown")
    app.expect_color(0)
    app.send(other_topic, b"0")
    app.expect_color(0)
    app.clock.now = 300_000
    app.cube.show_idle_if_due()
    app.expect_color(0)


def test_unknown_before_first_reading_and_after_idle(
    app: Harness,
    sensor_topics: tuple[bytes, bytes],
) -> None:
    app.clock.now = 130_000
    app.cube.show_idle_if_due()
    app.expect_color(240 / 360)
    app.send(sensor_topics[0], b"unknown")
    app.expect_color(0)


@pytest.mark.parametrize(
    ("topic", "payload", "hue", "brightness"),
    [
        (b"airgradient/co2", b"0", 100 / 360, 0.4),
        (b"airgradient/co2", b"850", 16.5 / 360, 0.6),
        (b"airgradient/co2", b"2000", 0, 0.6),
        (b"airgradient/pm25", b"0", 100 / 360, 0.4),
        (b"airgradient/pm25", b"100", 16.5 / 360, 0.6),
        (b"airgradient/pm25", b"2000", 0, 0.6),
    ],
)
def test_valid_reading_restores_normal_colors_and_idle(
    app: Harness,
    topic: bytes,
    payload: bytes,
    hue: float,
    brightness: float,
) -> None:
    app.send(topic, b"unknown")
    app.clock.now = 300_000
    app.send(topic, payload)
    app.cube.show_idle_if_due()
    app.expect_color(hue, brightness)
    app.clock.now += 130_000
    app.cube.show_idle_if_due()
    app.expect_color(240 / 360)


@pytest.mark.parametrize(
    "payload",
    [b"unknown", b"unavailable", b"", b"junk", b"-1", b"nan", b"inf", b"-inf"],
)
def test_invalid_reading_cannot_clear_warning(
    app: Harness,
    sensor_topics: tuple[bytes, bytes],
    payload: bytes,
) -> None:
    topic, _other_topic = sensor_topics
    app.send(topic, b"unknown")
    app.send(topic, payload)
    app.clock.now = 300_000
    app.cube.show_idle_if_due()
    app.expect_color(0)


def test_recovery_still_respects_high_other_sensor(
    app: Harness,
    sensor_topics: tuple[bytes, bytes],
) -> None:
    topic, other_topic = sensor_topics
    app.send(other_topic, b"1500")
    app.send(topic, b"unknown")
    app.send(topic, b"0")
    app.expect_color(0)


def test_off_on_preserves_warning_and_accepts_recovery_while_dark(
    app: Harness,
    sensor_topics: tuple[bytes, bytes],
) -> None:
    topic, _other_topic = sensor_topics
    app.send(b"led-cube/on", b"0")
    app.send(topic, b"unknown")
    app.expect_color(0, 0)
    app.clock.now = 300_000
    app.cube.show_idle_if_due()
    app.expect_color(0, 0)
    app.send(b"led-cube/on", b"1")
    app.expect_color(0)
    app.send(b"led-cube/on", b"0")
    app.send(topic, b"0")
    app.expect_color(100 / 360, 0)
    app.send(b"led-cube/on", b"1")
    app.expect_color(100 / 360, 0.4)


def test_unknown_on_non_sensor_topics_does_not_raise_warning(app: Harness) -> None:
    app.send(b"airgradient/pm25", b"0")
    app.send(b"led-cube/on", b"unknown")
    app.send(b"unrelated/topic", b"unknown")
    app.expect_color(100 / 360, 0.4)


def test_maintenance_color_overrides_warning(
    app: Harness,
    sensor_topics: tuple[bytes, bytes],
) -> None:
    app.send(sensor_topics[0], b"unknown")
    app.cube.show_maintenance()
    app.expect_color(0.78, 0.25)


def test_both_unknown_require_independent_recovery(
    app: Harness,
    sensor_topics: tuple[bytes, bytes],
) -> None:
    first, second = sensor_topics
    app.send(first, b"unknown")
    app.send(second, b"unknown")
    app.expect_color(0)
    app.send(first, b"0")
    app.expect_color(0)
    app.clock.now = 300_000
    app.cube.show_idle_if_due()
    app.expect_color(0)
    app.send(second, b"0")
    app.expect_color(100 / 360, 0.4)
