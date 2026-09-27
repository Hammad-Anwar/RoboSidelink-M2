import json
from pathlib import Path

import pytest

from robosidelink.config import load_config
from robosidelink.engine import SimulationEngine
from robosidelink.output import OutputExistsError, write_run_results


EXPECTED_FILES = {
    "config.original.yaml",
    "config.resolved.yaml",
    "metadata.json",
    "packets.csv",
    "transmissions.csv",
    "selector_diagnostics.csv",
    "metrics.json",
}


def _result_and_config():
    path = Path("configs/quickstart.yaml")
    config = load_config(path)
    return SimulationEngine(config).run(), config, path


def test_write_run_results_creates_documented_schema(tmp_path: Path) -> None:
    result, config, original = _result_and_config()
    destination = tmp_path / "run"

    written = write_run_results(
        result,
        config,
        destination,
        original_config_path=original,
    )

    assert written == destination.resolve()
    assert EXPECTED_FILES <= {path.name for path in destination.iterdir()}
    metadata = json.loads((destination / "metadata.json").read_text("utf-8"))
    assert {
        "simulator_version",
        "git_commit",
        "git_dirty",
        "seed",
        "timestamp_utc",
        "generation_horizon_slot",
        "final_executed_slot",
        "research_abstraction",
    } <= metadata.keys()
    assert isinstance(metadata["git_dirty"], bool)
    assert (destination / "packets.csv").read_text("utf-8").splitlines()[0]
    assert (destination / "transmissions.csv").read_text("utf-8").splitlines()[0]
    assert (destination / "selector_diagnostics.csv").read_text("utf-8").splitlines()[0]


def test_scientific_outputs_are_byte_reproducible(tmp_path: Path) -> None:
    first_result, first_config, original = _result_and_config()
    second_result, second_config, _ = _result_and_config()
    first = tmp_path / "first"
    second = tmp_path / "second"

    write_run_results(first_result, first_config, first, original_config_path=original)
    write_run_results(second_result, second_config, second, original_config_path=original)

    scientific_files = EXPECTED_FILES - {"metadata.json"}
    for filename in scientific_files:
        assert (first / filename).read_bytes() == (second / filename).read_bytes()


def test_existing_result_directory_is_preserved_without_overwrite(
    tmp_path: Path,
) -> None:
    result, config, original = _result_and_config()
    destination = tmp_path / "run"
    destination.mkdir()
    sentinel = destination / "keep.txt"
    sentinel.write_text("keep me", encoding="utf-8")

    with pytest.raises(OutputExistsError):
        write_run_results(
            result,
            config,
            destination,
            original_config_path=original,
        )

    assert sentinel.read_text("utf-8") == "keep me"


def test_explicit_overwrite_replaces_only_exact_target(tmp_path: Path) -> None:
    result, config, original = _result_and_config()
    destination = tmp_path / "run"
    destination.mkdir()
    (destination / "old.txt").write_text("old", encoding="utf-8")
    sibling = tmp_path / "sibling.txt"
    sibling.write_text("untouched", encoding="utf-8")

    write_run_results(
        result,
        config,
        destination,
        original_config_path=original,
        overwrite=True,
    )

    assert not (destination / "old.txt").exists()
    assert sibling.read_text("utf-8") == "untouched"
    assert EXPECTED_FILES <= {path.name for path in destination.iterdir()}
