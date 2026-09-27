from pathlib import Path

import pytest
import yaml

from robosidelink.config import ConfigError, load_config, ms_to_slots


PROJECT_ROOT = Path(__file__).resolve().parents[1]
QUICKSTART_CONFIG = PROJECT_ROOT / "configs" / "quickstart.yaml"


def _valid_config() -> dict:
    return {
        "simulation": {
            "duration_ms": 20.0,
            "slot_duration_ms": 0.25,
            "seed": 42,
        },
        "radio": {
            "num_subchannels": 4,
            "resource_width_subchannels": 1,
        },
        "traffic": {
            "kind": "periodic",
            "period_ms": 2.0,
            "jitter_ms": 0.0,
            "packet_size_bytes": 64,
            "deadline_ms": 3.0,
        },
        "scenario": {"num_robots": 2},
        "selector": {
            "policy": "random",
            "processing_delay_ms": 0.0,
            "mode2": {
                "sensing_window_ms": 100.0,
                "t1_ms": 0.0,
                "t2_ms": 2.0,
                "reservation_interval_ms": 2.0,
                "reselection_counter_min": 5,
                "reselection_counter_max": 15,
                "keep_probability": 0.5,
                "minimum_candidate_fraction": 0.2,
                "initial_evidence_threshold": 0,
            },
        },
    }


def _write_yaml(tmp_path: Path, data: dict) -> Path:
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return path


def test_ms_to_slots_converts_exact_multiple() -> None:
    assert ms_to_slots(0.5, 0.25, "traffic.period_ms") == 2


def test_ms_to_slots_rejects_non_integral_duration() -> None:
    with pytest.raises(ConfigError) as error:
        ms_to_slots(0.3, 0.25, "traffic.period_ms")

    message = str(error.value)
    assert "traffic.period_ms" in message
    assert "0.3" in message
    assert "whole number of slots" in message


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_ms_to_slots_rejects_non_finite_duration(value: float) -> None:
    with pytest.raises(ConfigError, match="finite"):
        ms_to_slots(value, 0.25, "traffic.period_ms")


def test_load_quickstart_config() -> None:
    config = load_config(QUICKSTART_CONFIG)

    assert config.simulation.duration_slots == 80
    assert config.simulation.slot_duration_ms == 0.25
    assert config.simulation.seed == 42
    assert config.scenario.num_robots == 2
    assert config.traffic.period_slots == 8
    assert config.traffic.deadline_slots == 12
    assert config.selector.mode2.t1_slots == 0
    assert config.selector.mode2.t2_slots == 8


def test_unknown_yaml_key_is_rejected(tmp_path: Path) -> None:
    data = _valid_config()
    data["simulation"]["duraton_ms"] = data["simulation"].pop("duration_ms")

    with pytest.raises(ConfigError) as error:
        load_config(_write_yaml(tmp_path, data))

    assert "simulation.duraton_ms" in str(error.value)
    assert "unknown configuration key" in str(error.value)


def test_jitter_must_be_smaller_than_period(tmp_path: Path) -> None:
    data = _valid_config()
    data["traffic"]["jitter_ms"] = 2.0

    with pytest.raises(ConfigError) as error:
        load_config(_write_yaml(tmp_path, data))

    assert "traffic.jitter_ms" in str(error.value)
    assert "smaller than traffic.period_ms" in str(error.value)


def test_paired_unicast_requires_even_robot_count(tmp_path: Path) -> None:
    data = _valid_config()
    data["scenario"]["num_robots"] = 3

    with pytest.raises(ConfigError) as error:
        load_config(_write_yaml(tmp_path, data))

    assert "scenario.num_robots" in str(error.value)
    assert "even integer" in str(error.value)
