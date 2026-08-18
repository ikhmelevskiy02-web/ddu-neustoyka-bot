import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "update_key_rate.py"


@pytest.fixture()
def temp_rates_file(tmp_path: Path) -> Path:
    source = REPO_ROOT / "src" / "data" / "key_rates.json"
    dest = tmp_path / "key_rates.json"
    dest.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    return dest


def run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
    )


def test_show_does_not_fail(temp_rates_file: Path):
    result = run("--path", str(temp_rates_file), "show")
    assert result.returncode == 0
    assert "%" in result.stdout


def test_add_valid_rate_persists(temp_rates_file: Path):
    result = run("--path", str(temp_rates_file), "add", "--date", "2026-09-14", "--rate", "13.75")
    assert result.returncode == 0

    payload = json.loads(temp_rates_file.read_text(encoding="utf-8"))
    assert payload["rates"]["2026-09-14"] == 13.75


def test_dry_run_does_not_persist(temp_rates_file: Path):
    before = temp_rates_file.read_text(encoding="utf-8")
    result = run(
        "--path", str(temp_rates_file), "add", "--date", "2026-09-14", "--rate", "13.75", "--dry-run"
    )
    assert result.returncode == 0
    after = temp_rates_file.read_text(encoding="utf-8")
    assert before == after


def test_implausible_rate_rejected(temp_rates_file: Path):
    result = run("--path", str(temp_rates_file), "add", "--date", "2026-09-14", "--rate", "137.5")
    assert result.returncode == 1

    payload = json.loads(temp_rates_file.read_text(encoding="utf-8"))
    assert "2026-09-14" not in payload["rates"]


def test_invalid_date_rejected(temp_rates_file: Path):
    result = run("--path", str(temp_rates_file), "add", "--date", "14-09-2026", "--rate", "13.75")
    assert result.returncode == 1


def test_same_value_is_noop(temp_rates_file: Path):
    run("--path", str(temp_rates_file), "add", "--date", "2026-09-14", "--rate", "13.75")
    before = temp_rates_file.read_text(encoding="utf-8")
    result = run("--path", str(temp_rates_file), "add", "--date", "2026-09-14", "--rate", "13.75")
    after = temp_rates_file.read_text(encoding="utf-8")
    assert result.returncode == 0
    assert before == after
