from dataclasses import replace
from pathlib import Path

import pandas as pd
import pytest

from experiments.run_density_sweep import (
    ExperimentError,
    aggregate_runs,
    run_density_sweep,
)
from robosidelink.config import load_config


def _small_config():
    config = load_config(Path("configs/quickstart.yaml"))
    return replace(
        config,
        simulation=replace(config.simulation, duration_slots=4),
    )


def test_density_sweep_runs_every_selector_count_and_seed(tmp_path: Path) -> None:
    destination = run_density_sweep(
        _small_config(),
        robot_counts=[2, 4],
        selectors=["random", "rel16-mode2-inspired"],
        seeds=[41, 42],
        output_dir=tmp_path / "density",
        bootstrap_resamples=100,
    )

    per_run = pd.read_csv(destination / "per_run.csv")
    assert len(per_run) == 8
    assert not per_run.duplicated(["selector", "num_robots", "seed"]).any()
    assert list(per_run[["selector", "num_robots", "seed"]].itertuples(index=False, name=None)) == sorted(
        per_run[["selector", "num_robots", "seed"]].itertuples(index=False, name=None)
    )
    for num_robots in [2, 4]:
        for seed in [41, 42]:
            pair = per_run[
                (per_run["num_robots"] == num_robots) & (per_run["seed"] == seed)
            ]
            assert set(pair["selector"]) == {
                "random",
                "rel16-mode2-inspired",
            }
            assert pair["generation_horizon_slot"].nunique() == 1
    assert (destination / "aggregate.csv").exists()
    assert (destination / "experiment_metadata.json").exists()


def test_invalid_selector_prevents_aggregate_success(tmp_path: Path) -> None:
    destination = tmp_path / "invalid-density"

    with pytest.raises(ExperimentError, match="unsupported selector"):
        run_density_sweep(
            _small_config(),
            robot_counts=[2],
            selectors=["invalid"],
            seeds=[42],
            output_dir=destination,
            bootstrap_resamples=100,
        )

    assert not (destination / "aggregate.csv").exists()


def test_aggregate_runs_uses_deterministic_percentile_bootstrap() -> None:
    per_run = pd.DataFrame(
        {
            "selector": ["random"] * 4,
            "num_robots": [2] * 4,
            "seed": [1, 2, 3, 4],
            "on_time_delivery_ratio": [1.0, 2.0, 5.0, 9.0],
            "collision_attempt_ratio": [0.0, 0.0, 0.0, 0.0],
            "end_to_end_latency_slots_p95": [1.0, 1.0, 1.0, 1.0],
            "resource_utilization": [0.1, 0.1, 0.1, 0.1],
        }
    )

    aggregate = aggregate_runs(
        per_run,
        bootstrap_seed=20260927,
        bootstrap_resamples=10_000,
    )

    row = aggregate.iloc[0]
    assert row["on_time_delivery_ratio_mean"] == pytest.approx(4.25)
    assert row["on_time_delivery_ratio_ci_low"] == pytest.approx(1.5)
    assert row["on_time_delivery_ratio_ci_high"] == pytest.approx(7.25)


def test_aggregate_runs_uses_null_interval_for_one_seed() -> None:
    per_run = pd.DataFrame(
        {
            "selector": ["random"],
            "num_robots": [2],
            "seed": [42],
            "on_time_delivery_ratio": [0.75],
            "collision_attempt_ratio": [0.25],
            "end_to_end_latency_slots_p95": [2.0],
            "resource_utilization": [0.5],
        }
    )

    row = aggregate_runs(per_run).iloc[0]

    assert row["on_time_delivery_ratio_mean"] == pytest.approx(0.75)
    assert pd.isna(row["on_time_delivery_ratio_ci_low"])
    assert pd.isna(row["on_time_delivery_ratio_ci_high"])

