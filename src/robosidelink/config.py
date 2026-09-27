"""Strict configuration loading and slot conversion."""

from __future__ import annotations

from dataclasses import dataclass
import math
from pathlib import Path
from typing import Any, Mapping

import yaml


class ConfigError(ValueError):
    """Raised when a simulation configuration is invalid."""


@dataclass(frozen=True)
class SimulationConfig:
    duration_slots: int
    slot_duration_ms: float
    seed: int


@dataclass(frozen=True)
class RadioConfig:
    num_subchannels: int
    resource_width_subchannels: int


@dataclass(frozen=True)
class TrafficConfig:
    kind: str
    period_slots: int
    jitter_slots: int
    packet_size_bytes: int
    deadline_slots: int


@dataclass(frozen=True)
class ScenarioConfig:
    num_robots: int


@dataclass(frozen=True)
class Mode2Config:
    sensing_window_slots: int
    t1_slots: int
    t2_slots: int
    reservation_interval_slots: int
    reselection_counter_min: int
    reselection_counter_max: int
    keep_probability: float
    minimum_candidate_fraction: float
    initial_evidence_threshold: int


@dataclass(frozen=True)
class SelectorConfig:
    policy: str
    processing_delay_slots: int
    mode2: Mode2Config


@dataclass(frozen=True)
class RunConfig:
    simulation: SimulationConfig
    radio: RadioConfig
    traffic: TrafficConfig
    scenario: ScenarioConfig
    selector: SelectorConfig


def ms_to_slots(value_ms: float, slot_duration_ms: float, key: str) -> int:
    """Convert milliseconds to slots without silently rounding."""
    if not math.isfinite(slot_duration_ms):
        raise ConfigError("simulation.slot_duration_ms must be finite")
    if not math.isfinite(value_ms):
        raise ConfigError(f"{key} must be finite; got {value_ms}")
    if slot_duration_ms <= 0:
        raise ConfigError("simulation.slot_duration_ms must be positive")
    if value_ms < 0:
        raise ConfigError(f"{key} must be non-negative; got {value_ms}")

    slots = value_ms / slot_duration_ms
    rounded = round(slots)
    if abs(slots - rounded) > 1e-9:
        raise ConfigError(
            f"{key}={value_ms} ms must equal a whole number of slots "
            f"for slot_duration_ms={slot_duration_ms}"
        )
    return int(rounded)


def _mapping(value: Any, key: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ConfigError(f"{key} must be a mapping")
    return value


def _validate_keys(
    data: Mapping[str, Any], *, key: str, allowed: set[str], required: set[str]
) -> None:
    unknown = sorted(set(data) - allowed)
    if unknown:
        full_key = f"{key}.{unknown[0]}" if key else unknown[0]
        raise ConfigError(f"unknown configuration key: {full_key}")
    missing = sorted(required - set(data))
    if missing:
        full_key = f"{key}.{missing[0]}" if key else missing[0]
        raise ConfigError(f"missing required configuration key: {full_key}")


def _positive_int(value: Any, key: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ConfigError(f"{key} must be a positive integer; got {value!r}")
    return value


def _non_negative_int(value: Any, key: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ConfigError(f"{key} must be a non-negative integer; got {value!r}")
    return value


def _number(value: Any, key: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ConfigError(f"{key} must be a number; got {value!r}")
    result = float(value)
    if not math.isfinite(result):
        raise ConfigError(f"{key} must be finite; got {value!r}")
    return result


def _probability(value: Any, key: str) -> float:
    result = _number(value, key)
    if not 0.0 <= result <= 1.0:
        raise ConfigError(f"{key} must be between 0 and 1; got {value!r}")
    return result


def load_config(path: Path) -> RunConfig:
    """Load and validate a YAML configuration file."""
    try:
        raw_value = yaml.safe_load(path.read_text(encoding="utf-8"))
    except OSError as error:
        raise ConfigError(f"cannot read configuration {path}: {error}") from error
    except yaml.YAMLError as error:
        raise ConfigError(f"invalid YAML in {path}: {error}") from error

    raw = _mapping(raw_value, "configuration")
    top_keys = {"simulation", "radio", "traffic", "scenario", "selector"}
    _validate_keys(raw, key="", allowed=top_keys, required=top_keys)

    simulation = _mapping(raw["simulation"], "simulation")
    _validate_keys(
        simulation,
        key="simulation",
        allowed={"duration_ms", "slot_duration_ms", "seed"},
        required={"duration_ms", "slot_duration_ms", "seed"},
    )
    slot_duration_ms = _number(
        simulation["slot_duration_ms"], "simulation.slot_duration_ms"
    )
    if slot_duration_ms <= 0:
        raise ConfigError("simulation.slot_duration_ms must be positive")
    duration_slots = ms_to_slots(
        _number(simulation["duration_ms"], "simulation.duration_ms"),
        slot_duration_ms,
        "simulation.duration_ms",
    )
    if duration_slots <= 0:
        raise ConfigError("simulation.duration_ms must be at least one slot")
    seed = _non_negative_int(simulation["seed"], "simulation.seed")

    radio = _mapping(raw["radio"], "radio")
    _validate_keys(
        radio,
        key="radio",
        allowed={"num_subchannels", "resource_width_subchannels"},
        required={"num_subchannels", "resource_width_subchannels"},
    )
    num_subchannels = _positive_int(
        radio["num_subchannels"], "radio.num_subchannels"
    )
    resource_width = _positive_int(
        radio["resource_width_subchannels"],
        "radio.resource_width_subchannels",
    )
    if resource_width > num_subchannels:
        raise ConfigError(
            "radio.resource_width_subchannels must not exceed radio.num_subchannels"
        )

    traffic = _mapping(raw["traffic"], "traffic")
    traffic_keys = {
        "kind",
        "period_ms",
        "jitter_ms",
        "packet_size_bytes",
        "deadline_ms",
    }
    _validate_keys(traffic, key="traffic", allowed=traffic_keys, required=traffic_keys)
    kind = traffic["kind"]
    if kind not in {"periodic", "jittered-periodic"}:
        raise ConfigError(
            "traffic.kind must be 'periodic' or 'jittered-periodic'"
        )
    period_slots = ms_to_slots(
        _number(traffic["period_ms"], "traffic.period_ms"),
        slot_duration_ms,
        "traffic.period_ms",
    )
    jitter_slots = ms_to_slots(
        _number(traffic["jitter_ms"], "traffic.jitter_ms"),
        slot_duration_ms,
        "traffic.jitter_ms",
    )
    deadline_slots = ms_to_slots(
        _number(traffic["deadline_ms"], "traffic.deadline_ms"),
        slot_duration_ms,
        "traffic.deadline_ms",
    )
    if period_slots <= 0:
        raise ConfigError("traffic.period_ms must be at least one slot")
    if deadline_slots <= 0:
        raise ConfigError("traffic.deadline_ms must be at least one slot")
    if jitter_slots >= period_slots:
        raise ConfigError(
            "traffic.jitter_ms must be smaller than traffic.period_ms"
        )
    packet_size = _positive_int(
        traffic["packet_size_bytes"], "traffic.packet_size_bytes"
    )

    scenario = _mapping(raw["scenario"], "scenario")
    _validate_keys(
        scenario,
        key="scenario",
        allowed={"num_robots"},
        required={"num_robots"},
    )
    num_robots = _positive_int(scenario["num_robots"], "scenario.num_robots")
    if num_robots < 2 or num_robots % 2:
        raise ConfigError(
            "scenario.num_robots must be an even integer of at least 2 "
            "for paired unicast"
        )

    selector = _mapping(raw["selector"], "selector")
    _validate_keys(
        selector,
        key="selector",
        allowed={"policy", "processing_delay_ms", "mode2"},
        required={"policy", "processing_delay_ms", "mode2"},
    )
    policy = selector["policy"]
    if policy not in {"random", "rel16-mode2-inspired"}:
        raise ConfigError(
            "selector.policy must be 'random' or 'rel16-mode2-inspired'"
        )
    processing_delay_slots = ms_to_slots(
        _number(selector["processing_delay_ms"], "selector.processing_delay_ms"),
        slot_duration_ms,
        "selector.processing_delay_ms",
    )

    mode2 = _mapping(selector["mode2"], "selector.mode2")
    mode2_keys = {
        "sensing_window_ms",
        "t1_ms",
        "t2_ms",
        "reservation_interval_ms",
        "reselection_counter_min",
        "reselection_counter_max",
        "keep_probability",
        "minimum_candidate_fraction",
        "initial_evidence_threshold",
    }
    _validate_keys(
        mode2,
        key="selector.mode2",
        allowed=mode2_keys,
        required=mode2_keys,
    )
    sensing_window_slots = ms_to_slots(
        _number(mode2["sensing_window_ms"], "selector.mode2.sensing_window_ms"),
        slot_duration_ms,
        "selector.mode2.sensing_window_ms",
    )
    t1_slots = ms_to_slots(
        _number(mode2["t1_ms"], "selector.mode2.t1_ms"),
        slot_duration_ms,
        "selector.mode2.t1_ms",
    )
    t2_slots = ms_to_slots(
        _number(mode2["t2_ms"], "selector.mode2.t2_ms"),
        slot_duration_ms,
        "selector.mode2.t2_ms",
    )
    reservation_interval_slots = ms_to_slots(
        _number(
            mode2["reservation_interval_ms"],
            "selector.mode2.reservation_interval_ms",
        ),
        slot_duration_ms,
        "selector.mode2.reservation_interval_ms",
    )
    if sensing_window_slots <= 0:
        raise ConfigError("selector.mode2.sensing_window_ms must be positive")
    if t1_slots > t2_slots:
        raise ConfigError("selector.mode2.t1_ms must not exceed selector.mode2.t2_ms")
    if reservation_interval_slots <= 0:
        raise ConfigError("selector.mode2.reservation_interval_ms must be positive")
    counter_min = _positive_int(
        mode2["reselection_counter_min"],
        "selector.mode2.reselection_counter_min",
    )
    counter_max = _positive_int(
        mode2["reselection_counter_max"],
        "selector.mode2.reselection_counter_max",
    )
    if counter_min > counter_max:
        raise ConfigError(
            "selector.mode2.reselection_counter_min must not exceed "
            "selector.mode2.reselection_counter_max"
        )

    return RunConfig(
        simulation=SimulationConfig(
            duration_slots=duration_slots,
            slot_duration_ms=slot_duration_ms,
            seed=seed,
        ),
        radio=RadioConfig(
            num_subchannels=num_subchannels,
            resource_width_subchannels=resource_width,
        ),
        traffic=TrafficConfig(
            kind=kind,
            period_slots=period_slots,
            jitter_slots=jitter_slots,
            packet_size_bytes=packet_size,
            deadline_slots=deadline_slots,
        ),
        scenario=ScenarioConfig(num_robots=num_robots),
        selector=SelectorConfig(
            policy=policy,
            processing_delay_slots=processing_delay_slots,
            mode2=Mode2Config(
                sensing_window_slots=sensing_window_slots,
                t1_slots=t1_slots,
                t2_slots=t2_slots,
                reservation_interval_slots=reservation_interval_slots,
                reselection_counter_min=counter_min,
                reselection_counter_max=counter_max,
                keep_probability=_probability(
                    mode2["keep_probability"],
                    "selector.mode2.keep_probability",
                ),
                minimum_candidate_fraction=_probability(
                    mode2["minimum_candidate_fraction"],
                    "selector.mode2.minimum_candidate_fraction",
                ),
                initial_evidence_threshold=_non_negative_int(
                    mode2["initial_evidence_threshold"],
                    "selector.mode2.initial_evidence_threshold",
                ),
            ),
        ),
    )
