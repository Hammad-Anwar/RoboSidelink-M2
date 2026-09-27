from pathlib import Path

import pandas as pd

from scripts.plot_density_sweep import plot_density_sweep


def test_plot_density_sweep_creates_four_nonempty_pngs(tmp_path: Path) -> None:
    input_directory = tmp_path / "input"
    output_directory = tmp_path / "plots"
    input_directory.mkdir()
    rows = []
    for selector, offset in [("random", 0.0), ("rel16-mode2-inspired", 0.1)]:
        for nodes in [2, 4]:
            row = {"selector": selector, "num_robots": nodes, "seed_count": 4}
            for metric, value in {
                "on_time_delivery_ratio": 0.9 - offset,
                "collision_attempt_ratio": 0.1 + offset,
                "end_to_end_latency_slots_p95": 2.0 + offset,
                "resource_utilization": 0.5 + offset,
            }.items():
                row[f"{metric}_mean"] = value
                row[f"{metric}_ci_low"] = value - 0.05
                row[f"{metric}_ci_high"] = value + 0.05
            rows.append(row)
    pd.DataFrame(rows).to_csv(input_directory / "aggregate.csv", index=False)

    created = plot_density_sweep(input_directory, output_directory)

    assert {path.name for path in created} == {
        "on_time_delivery.png",
        "collision_attempt_ratio.png",
        "p95_end_to_end_latency.png",
        "resource_utilization.png",
    }
    assert all(path.stat().st_size > 0 for path in created)
