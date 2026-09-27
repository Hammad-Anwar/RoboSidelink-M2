import os
from pathlib import Path
import subprocess
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _run(*arguments: str) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["PYTHONIOENCODING"] = "utf-8"
    return subprocess.run(
        [sys.executable, *arguments],
        cwd=PROJECT_ROOT,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )


def test_documented_help_commands_succeed() -> None:
    root = _run("-m", "robosidelink", "--help")
    simulate = _run("-m", "robosidelink", "simulate", "--help")

    assert root.returncode == 0, root.stderr
    assert simulate.returncode == 0, simulate.stderr
    assert "simulate" in root.stdout
    assert "--config" in simulate.stdout


def test_documented_quickstart_command_succeeds(tmp_path: Path) -> None:
    output = tmp_path / "readme-quickstart"

    completed = _run(
        "-m",
        "robosidelink",
        "simulate",
        "--config",
        "configs/quickstart.yaml",
        "--output",
        str(output),
    )

    assert completed.returncode == 0, completed.stderr
    assert (output / "metrics.json").exists()


def test_reviewer_documentation_files_exist() -> None:
    expected = [
        PROJECT_ROOT / "README.md",
        PROJECT_ROOT / "docs" / "model-scope.md",
        PROJECT_ROOT / "docs" / "rel16-traceability.md",
        PROJECT_ROOT / "docs" / "metrics.md",
        PROJECT_ROOT / "docs" / "project-plan.md",
        PROJECT_ROOT / "configs" / "quickstart.yaml",
        PROJECT_ROOT / "configs" / "baseline.yaml",
        PROJECT_ROOT / "configs" / "density_sweep.yaml",
    ]

    assert all(path.is_file() for path in expected)
