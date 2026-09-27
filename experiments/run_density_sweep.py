"""Run paired-seed robot-density comparisons."""

from __future__ import annotations

import argparse
from dataclasses import replace
import json
from pathlib import Path
import shutil
from typing import Sequence
import uuid

import numpy as np
import pandas as pd
import yaml

from robosidelink.config import RunConfig, load_config
from robosidelink.engine import SimulationEngine
from robosidelink.metrics import MetricsCollector
from robosidelink.output import OutputExistsError, write_run_results


SUPPORTED_SELECTORS = {"random", "rel16-mode2-inspired"}
AGGREGATE_METRICS = (
    "on_time_delivery_ratio",
    "collision_attempt_ratio",
    "end_to_end_latency_slots_p95",
    "resource_utilization",
)


class ExperimentError(RuntimeError):
    """Raised when a density experiment cannot produce a complete dataset."""


def run_density_sweep(
    base_config: RunConfig,
    *,
    robot_counts: Sequence[int],
    selectors: Sequence[str],
    seeds: Sequence[int],
    output_dir: Path,
    overwrite: bool = False,
    bootstrap_seed: int = 20260927,
    bootstrap_resamples: int = 10_000,
) -> Path:
    """Run every selector/count/seed combination into an atomic directory."""
    _validate_experiment(robot_counts, selectors, seeds, bootstrap_resamples)
    destination = output_dir.resolve()
    if destination.exists() and any(destination.iterdir()) and not overwrite:
        raise OutputExistsError(
            f"experiment directory already exists and is not empty: {destination}"
        )
    if destination == Path(destination.anchor):
        raise ExperimentError("refusing to use a filesystem root as experiment output")

    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.parent / f".{destination.name}.tmp-{uuid.uuid4().hex}"
    temporary.mkdir()
    rows: list[dict] = []
    try:
        for selector in sorted(selectors):
            for num_robots in sorted(robot_counts):
                for seed in sorted(seeds):
                    config = replace(
                        base_config,
                        simulation=replace(base_config.simulation, seed=seed),
                        scenario=replace(
                            base_config.scenario,
                            num_robots=num_robots,
                        ),
                        selector=replace(
                            base_config.selector,
                            policy=selector,
                        ),
                    )
                    result = SimulationEngine(config).run()
                    run_directory = (
                        temporary
                        / "runs"
                        / selector
                        / f"nodes-{num_robots}"
                        / f"seed-{seed}"
                    )
                    write_run_results(result, config, run_directory)
                    metrics = MetricsCollector().summary(result)
                    rows.append(
                        {
                            "selector": selector,
                            "num_robots": num_robots,
                            "seed": seed,
                            "generation_horizon_slot": (
                                result.generation_horizon_slot
                            ),
                            "final_executed_slot": result.final_executed_slot,
                            **metrics,
                        }
                    )

        per_run = pd.DataFrame(rows).sort_values(
            ["selector", "num_robots", "seed"], ignore_index=True
        )
        aggregate = aggregate_runs(
            per_run,
            bootstrap_seed=bootstrap_seed,
            bootstrap_resamples=bootstrap_resamples,
        )
        per_run.to_csv(temporary / "per_run.csv", index=False, lineterminator="\n")
        aggregate.to_csv(
            temporary / "aggregate.csv", index=False, lineterminator="\n"
        )
        (temporary / "experiment_metadata.json").write_text(
            json.dumps(
                {
                    "robot_counts": sorted(robot_counts),
                    "selectors": sorted(selectors),
                    "seeds": sorted(seeds),
                    "confidence_interval_method": "percentile bootstrap",
                    "confidence_level": 0.95,
                    "bootstrap_resamples": bootstrap_resamples,
                    "bootstrap_seed": bootstrap_seed,
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        if destination.exists():
            shutil.rmtree(destination)
        temporary.replace(destination)
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise
    return destination


def aggregate_runs(
    per_run: pd.DataFrame,
    bootstrap_seed: int = 20260927,
    bootstrap_resamples: int = 10_000,
) -> pd.DataFrame:
    """Aggregate per-seed metrics with deterministic percentile intervals."""
    rng = np.random.default_rng(bootstrap_seed)
    rows: list[dict] = []
    grouped = per_run.groupby(["selector", "num_robots"], sort=True)
    for (selector, num_robots), group in grouped:
        row: dict[str, str | int | float] = {
            "selector": selector,
            "num_robots": int(num_robots),
            "seed_count": int(group["seed"].nunique()),
        }
        for metric in AGGREGATE_METRICS:
            values = group[metric].dropna().to_numpy(dtype=float)
            if len(values) == 0:
                mean = low = high = float("nan")
            else:
                mean = float(values.mean())
                if len(values) == 1:
                    low = high = float("nan")
                else:
                    resampled = rng.choice(
                        values,
                        size=(bootstrap_resamples, len(values)),
                        replace=True,
                    ).mean(axis=1)
                    low, high = (
                        float(value)
                        for value in np.quantile(resampled, [0.025, 0.975])
                    )
            row[f"{metric}_mean"] = mean
            row[f"{metric}_ci_low"] = low
            row[f"{metric}_ci_high"] = high
        rows.append(row)
    return pd.DataFrame(rows).sort_values(
        ["selector", "num_robots"], ignore_index=True
    )


def _validate_experiment(
    robot_counts: Sequence[int],
    selectors: Sequence[str],
    seeds: Sequence[int],
    bootstrap_resamples: int,
) -> None:
    if not robot_counts or any(value < 2 or value % 2 for value in robot_counts):
        raise ExperimentError("robot counts must be non-empty even integers >= 2")
    unsupported = sorted(set(selectors) - SUPPORTED_SELECTORS)
    if unsupported:
        raise ExperimentError(f"unsupported selector: {unsupported[0]}")
    if not selectors:
        raise ExperimentError("at least one selector is required")
    if not seeds or any(seed < 0 for seed in seeds):
        raise ExperimentError("seeds must be non-empty non-negative integers")
    if bootstrap_resamples <= 0:
        raise ExperimentError("bootstrap_resamples must be positive")


def _load_experiment_file(path: Path) -> tuple[RunConfig, dict]:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or set(raw) != {"base_config", "experiment"}:
        raise ExperimentError(
            "density config must contain exactly base_config and experiment"
        )
    experiment = raw["experiment"]
    expected = {
        "robot_counts",
        "selectors",
        "seeds",
        "bootstrap_seed",
        "bootstrap_resamples",
    }
    if not isinstance(experiment, dict) or set(experiment) != expected:
        raise ExperimentError(
            "experiment must define robot_counts, selectors, seeds, "
            "bootstrap_seed, and bootstrap_resamples"
        )
    base_path = (path.parent / raw["base_config"]).resolve()
    return load_config(base_path), experiment


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--overwrite", action="store_true")
    arguments = parser.parse_args(argv)
    try:
        base, experiment = _load_experiment_file(arguments.config)
        destination = run_density_sweep(
            base,
            robot_counts=experiment["robot_counts"],
            selectors=experiment["selectors"],
            seeds=experiment["seeds"],
            output_dir=arguments.output,
            overwrite=arguments.overwrite,
            bootstrap_seed=experiment["bootstrap_seed"],
            bootstrap_resamples=experiment["bootstrap_resamples"],
        )
    except (ExperimentError, OutputExistsError, OSError, ValueError) as error:
        print(f"error: {error}", file=__import__("sys").stderr)
        return 2
    print(f"Experiment directory: {destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

