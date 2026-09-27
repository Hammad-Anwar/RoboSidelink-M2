"""Command-line interface for reproducible simulator runs."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from typing import Sequence
import traceback

from robosidelink.config import ConfigError, load_config
from robosidelink.engine import SimulationEngine
from robosidelink.metrics import MetricsCollector
from robosidelink.output import OutputExistsError, write_run_results


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="robosidelink",
        description="Run the RoboSidelink-M2 research simulator.",
    )
    subcommands = parser.add_subparsers(dest="command", required=True)
    simulate = subcommands.add_parser("simulate", help="run one simulation")
    simulate.add_argument("--config", type=Path, required=True)
    simulate.add_argument("--output", type=Path)
    simulate.add_argument("--overwrite", action="store_true")
    simulate.add_argument("--verbose", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    arguments = _parser().parse_args(argv)
    try:
        if arguments.command == "simulate":
            return _simulate(arguments)
    except (ConfigError, OutputExistsError, OSError, ValueError) as error:
        if arguments.verbose:
            traceback.print_exc()
        else:
            print(f"error: {error}", file=sys.stderr)
        return 2
    return 2


def _simulate(arguments: argparse.Namespace) -> int:
    config = load_config(arguments.config)
    result = SimulationEngine(config).run()
    output = arguments.output or _default_output(config.simulation.seed)
    destination = write_run_results(
        result,
        config,
        output,
        original_config_path=arguments.config,
        overwrite=arguments.overwrite,
    )
    metrics = MetricsCollector().summary(result)
    concise = {
        "generated_packets": metrics["generated_packets"],
        "on_time_delivery_ratio": metrics["on_time_delivery_ratio"],
        "collision_attempt_ratio": metrics["collision_attempt_ratio"],
    }
    print(json.dumps(concise, indent=2, sort_keys=True))
    print(f"Result directory: {destination}")
    return 0


def _default_output(seed: int) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return Path("results") / f"run-{stamp}-seed-{seed}"
