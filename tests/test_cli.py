import os
from pathlib import Path
import subprocess
import sys

import yaml

from robosidelink.cli import main


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _run_cli(*arguments: str) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["PYTHONIOENCODING"] = "utf-8"
    return subprocess.run(
        [sys.executable, "-m", "robosidelink", *arguments],
        cwd=PROJECT_ROOT,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )


def test_simulate_command_runs_quickstart_and_prints_result_path(
    tmp_path: Path,
) -> None:
    output = tmp_path / "quickstart"

    completed = _run_cli(
        "simulate",
        "--config",
        "configs/quickstart.yaml",
        "--output",
        str(output),
    )

    assert completed.returncode == 0, completed.stderr
    assert str(output.resolve()) in completed.stdout
    assert "on_time_delivery_ratio" in completed.stdout
    assert (output / "metrics.json").exists()


def test_invalid_configuration_is_concise_without_traceback(tmp_path: Path) -> None:
    invalid = tmp_path / "invalid.yaml"
    invalid.write_text(yaml.safe_dump({"unexpected": True}), encoding="utf-8")

    completed = _run_cli("simulate", "--config", str(invalid))

    assert completed.returncode != 0
    assert "unknown configuration key" in completed.stderr
    assert "Traceback" not in completed.stderr


def test_verbose_invalid_configuration_includes_traceback(tmp_path: Path) -> None:
    invalid = tmp_path / "invalid.yaml"
    invalid.write_text(yaml.safe_dump({"unexpected": True}), encoding="utf-8")

    completed = _run_cli("simulate", "--config", str(invalid), "--verbose")

    assert completed.returncode != 0
    assert "Traceback" in completed.stderr


def test_main_directly_runs_simulation_for_coverage(
    tmp_path: Path, capsys
) -> None:
    output = tmp_path / "direct"

    exit_code = main(
        [
            "simulate",
            "--config",
            "configs/quickstart.yaml",
            "--output",
            str(output),
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert str(output.resolve()) in captured.out
    assert (output / "metrics.json").exists()


def test_main_directly_reports_expected_error_for_coverage(
    tmp_path: Path, capsys
) -> None:
    invalid = tmp_path / "invalid.yaml"
    invalid.write_text(yaml.safe_dump({"unexpected": True}), encoding="utf-8")

    exit_code = main(["simulate", "--config", str(invalid)])

    captured = capsys.readouterr()
    assert exit_code == 2
    assert "unknown configuration key" in captured.err
