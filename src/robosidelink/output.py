"""Atomic, reproducible simulation-result persistence."""

from __future__ import annotations

import csv
from dataclasses import asdict
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import subprocess
import uuid

import yaml

from robosidelink import __version__
from robosidelink.config import RunConfig
from robosidelink.metrics import MetricsCollector
from robosidelink.models import PacketStatus, SimulationResult


class OutputExistsError(FileExistsError):
    """Raised when a result directory would be overwritten implicitly."""


_TERMINAL_STATUSES = {
    PacketStatus.DELIVERED_ON_TIME,
    PacketStatus.COLLIDED,
    PacketStatus.EXPIRED_WHILE_QUEUED,
    PacketStatus.EXPIRED_WHILE_WAITING,
    PacketStatus.NO_FEASIBLE_RESOURCE,
}


def write_run_results(
    result: SimulationResult,
    config: RunConfig,
    output_dir: Path,
    *,
    original_config_path: Path | None = None,
    overwrite: bool = False,
) -> Path:
    """Write one complete result directory and return its absolute path."""
    destination = output_dir.resolve()
    if destination.exists() and any(destination.iterdir()) and not overwrite:
        raise OutputExistsError(
            f"result directory already exists and is not empty: {destination}"
        )
    if destination == Path(destination.anchor):
        raise ValueError("refusing to use a filesystem root as an output directory")

    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.parent / f".{destination.name}.tmp-{uuid.uuid4().hex}"
    temporary.mkdir()
    try:
        _write_original_config(temporary, config, original_config_path)
        (temporary / "config.resolved.yaml").write_text(
            yaml.safe_dump(asdict(config), sort_keys=True),
            encoding="utf-8",
        )
        _write_packets(temporary / "packets.csv", result)
        _write_transmissions(temporary / "transmissions.csv", result)
        _write_selector_diagnostics(
            temporary / "selector_diagnostics.csv", result
        )
        metrics = MetricsCollector().summary(result)
        _write_json(temporary / "metrics.json", metrics)
        git_commit, git_dirty = _git_state()
        _write_json(
            temporary / "metadata.json",
            {
                "simulator_version": __version__,
                "git_commit": git_commit,
                "git_dirty": git_dirty,
                "seed": config.simulation.seed,
                "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                "generation_horizon_slot": result.generation_horizon_slot,
                "final_executed_slot": result.final_executed_slot,
                "research_abstraction": True,
            },
        )

        if destination.exists():
            shutil.rmtree(destination)
        temporary.replace(destination)
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise
    return destination


def _write_original_config(
    directory: Path,
    config: RunConfig,
    original_config_path: Path | None,
) -> None:
    target = directory / "config.original.yaml"
    if original_config_path is not None:
        shutil.copyfile(original_config_path, target)
    else:
        target.write_text(
            yaml.safe_dump(asdict(config), sort_keys=True),
            encoding="utf-8",
        )


def _write_packets(path: Path, result: SimulationResult) -> None:
    terminal = {
        record.packet_id: record
        for record in result.lifecycle_records
        if record.status in _TERMINAL_STATUSES
    }
    fieldnames = [
        "packet_id",
        "source_id",
        "destination_id",
        "generation_slot",
        "deadline_slot",
        "payload_size_bytes",
        "priority",
        "terminal_status",
        "terminal_slot",
    ]
    rows = []
    for packet in result.generated_packets:
        record = terminal.get(packet.packet_id)
        rows.append(
            {
                **asdict(packet),
                "terminal_status": record.status.value if record else "",
                "terminal_slot": record.slot if record else "",
            }
        )
    _write_csv(path, fieldnames, rows)


def _write_transmissions(path: Path, result: SimulationResult) -> None:
    fieldnames = [
        "packet_id",
        "source_id",
        "destination_id",
        "slot",
        "start_subchannel",
        "width",
        "status",
        "reservation_interval_slots",
    ]
    rows = [
        {
            "packet_id": item.packet.packet_id,
            "source_id": item.packet.source_id,
            "destination_id": item.packet.destination_id,
            "slot": item.resource.slot,
            "start_subchannel": item.resource.start_subchannel,
            "width": item.resource.width,
            "status": item.status.value,
            "reservation_interval_slots": item.reservation_interval_slots or "",
        }
        for item in result.transmissions
    ]
    _write_csv(path, fieldnames, rows)


def _write_selector_diagnostics(path: Path, result: SimulationResult) -> None:
    fieldnames = [
        "node_id",
        "packet_id",
        "policy",
        "request_slot",
        "decision_slot",
        "initial_candidate_count",
        "excluded_candidate_count",
        "retained_candidate_count",
        "relaxation_level",
        "selected_slot",
        "selected_start_subchannel",
        "selected_width",
    ]
    rows = []
    for item in result.selector_diagnostics:
        resource = item.selected_resource
        rows.append(
            {
                "node_id": item.node_id,
                "packet_id": item.packet_id,
                "policy": item.policy,
                "request_slot": item.request_slot,
                "decision_slot": item.decision_slot,
                "initial_candidate_count": item.initial_candidate_count,
                "excluded_candidate_count": item.excluded_candidate_count,
                "retained_candidate_count": item.retained_candidate_count,
                "relaxation_level": item.relaxation_level,
                "selected_slot": resource.slot if resource else "",
                "selected_start_subchannel": (
                    resource.start_subchannel if resource else ""
                ),
                "selected_width": resource.width if resource else "",
            }
        )
    _write_csv(path, fieldnames, rows)


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _write_json(path: Path, value: dict) -> None:
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def _git_state() -> tuple[str, bool]:
    commit_result = subprocess.run(
        ["git", "rev-parse", "--verify", "HEAD"],
        capture_output=True,
        text=True,
        check=False,
    )
    status_result = subprocess.run(
        ["git", "status", "--porcelain"],
        capture_output=True,
        text=True,
        check=False,
    )
    commit = (
        commit_result.stdout.strip()
        if commit_result.returncode == 0
        else "uncommitted"
    )
    dirty = status_result.returncode == 0 and bool(status_result.stdout.strip())
    return commit, dirty
