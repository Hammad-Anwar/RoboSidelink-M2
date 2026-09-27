"""Create density-sweep figures from aggregate results."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


_PLOTS = {
    "on_time_delivery_ratio": (
        "on_time_delivery.png",
        "On-time delivery ratio",
    ),
    "collision_attempt_ratio": (
        "collision_attempt_ratio.png",
        "Collision-attempt ratio",
    ),
    "end_to_end_latency_slots_p95": (
        "p95_end_to_end_latency.png",
        "P95 end-to-end latency (slots)",
    ),
    "resource_utilization": (
        "resource_utilization.png",
        "Resource utilization",
    ),
}


def plot_density_sweep(
    input_directory: Path, output_directory: Path
) -> tuple[Path, ...]:
    aggregate_path = input_directory / "aggregate.csv"
    data = pd.read_csv(aggregate_path)
    output_directory.mkdir(parents=True, exist_ok=True)
    created: list[Path] = []

    for metric, (filename, ylabel) in _PLOTS.items():
        figure, axis = plt.subplots(figsize=(7.2, 4.6))
        for selector, group in data.groupby("selector", sort=True):
            group = group.sort_values("num_robots")
            mean = group[f"{metric}_mean"].to_numpy(dtype=float)
            low = group[f"{metric}_ci_low"].to_numpy(dtype=float)
            high = group[f"{metric}_ci_high"].to_numpy(dtype=float)
            lower_error = np.nan_to_num(mean - low, nan=0.0)
            upper_error = np.nan_to_num(high - mean, nan=0.0)
            axis.errorbar(
                group["num_robots"],
                mean,
                yerr=np.vstack([lower_error, upper_error]),
                marker="o",
                capsize=4,
                label=selector,
            )
        axis.set_xlabel("Number of robots")
        axis.set_ylabel(ylabel)
        axis.set_title(
            f"{ylabel} vs robot density\n"
            "Research abstraction; deterministic collision channel"
        )
        axis.grid(True, alpha=0.3)
        axis.legend()
        figure.tight_layout()
        destination = output_directory / filename
        figure.savefig(destination, dpi=180)
        plt.close(figure)
        created.append(destination)
    return tuple(created)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args(argv)
    try:
        created = plot_density_sweep(arguments.input, arguments.output)
    except (OSError, ValueError, KeyError) as error:
        print(f"error: {error}", file=__import__("sys").stderr)
        return 2
    for path in created:
        print(path.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

