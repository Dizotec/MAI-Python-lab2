import json
import os
import subprocess
import sys
from pathlib import Path

from tests import get_data


def run_cli(tmp_path: Path, *args: str) -> subprocess.CompletedProcess[str]:

    # CLI в отдельном процессе.
    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[1] / "src")
    env["PYTHONIOENCODING"] = "utf-8"

    return subprocess.run(
        [sys.executable, "-m", "streamstats", *args],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=10,
        check=False,
    )


def test_help(tmp_path: Path) -> None:

    result = run_cli(tmp_path, "--help")
    assert result.returncode == 0
    assert "analyze" in result.stdout


def test_empty_report(tmp_path: Path) -> None:

    path = tmp_path / "empty.jsonl"
    path.write_text("", encoding="utf-8")
    result = run_cli(tmp_path, "analyze", str(path), "--format", "jsonl")
    assert result.returncode == 0, result.stdout + result.stderr
    report = json.loads(result.stdout)
    assert report["total_events"] == 0
    assert report["first_timestamp"] is None
    assert report["last_timestamp"] is None

    result = run_cli(
        tmp_path, "analyze", str(path), "--format", "jsonl", "--skip-invalid"
    )
    assert json.loads(result.stdout)["skipped_lines"] == 0


def test_multiple_files_report(tmp_path: Path) -> None:

    data = get_data()
    # Несколько файлов, кириллица.
    first = tmp_path / "first.jsonl"
    second = tmp_path / "second.jsonl"
    data["source"] = "сервис"
    text = json.dumps(data, ensure_ascii=False) + "\n"
    first.write_text(text, encoding="utf-8")
    second.write_text(text, encoding="utf-8")
    output = tmp_path / "report.json"
    result = run_cli(
        tmp_path,
        "analyze",
        str(first),
        str(second),
        "--format",
        "jsonl",
        "--output",
        str(output),
    )
    assert result.returncode == 0, result.stdout + result.stderr
    report_text = output.read_text(encoding="utf-8")
    report = json.loads(report_text)
    assert report["total_events"] == 2
    assert report["sources"] == {"сервис": 2}
    assert report["first_timestamp"] == "2026-10-24T10:00:00+00:00"
    assert "сервис" in report_text
    assert first.read_text(encoding="utf-8") == text
    assert second.read_text(encoding="utf-8") == text


def test_cli_error_and_skip(tmp_path: Path) -> None:

    data = get_data()

    path = tmp_path / "bad.jsonl"
    path.write_text(json.dumps(data) + "\n{broken}\n", encoding="utf-8")
    result = run_cli(tmp_path, "analyze", str(path), "--format", "jsonl")
    assert result.returncode == 2
    assert str(path) in result.stdout + result.stderr
    assert "2" in result.stdout + result.stderr
    output = tmp_path / "report.json"
    result = run_cli(
        tmp_path,
        "analyze",
        str(path),
        "--format",
        "jsonl",
        "--output",
        str(output),
        "--skip-invalid",
    )
    assert result.returncode == 0, result.stdout + result.stderr
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["total_events"] == 1
    assert report["skipped_lines"] == 1


def test_cli_invalid_arguments(tmp_path: Path) -> None:

    cases = [
        [],
        ["analyze"],
        ["analyze", "file", "--format"],
        ["analyze", "file", "--format", "xml"],
        ["analyze", "file", "--format", "jsonl", "--output"],
        ["analyze", "file", "--skip-invalid", "--format", "jsonl"],
        ["analyze", "file", "--format", "jsonl", "--top", "0"],
        ["analyze", "file", "--format", "jsonl", "--unknown"],
        ["analyze", "file", "--format", "jsonl", "--level", "BAD"],
        ["analyze", "file", "--format", "jsonl", "--source", " "],
        [
            "analyze",
            "file",
            "--format",
            "jsonl",
            "--start",
            "2026-11-03",
            "--end",
            "2026-11-01",
        ],
        ["analyze", "missing.jsonl", "--format", "jsonl"],
        ["analyze", "file.csv", "--format", "csv", "--follow"],
    ]

    for args in cases:
        result = run_cli(tmp_path, *args)
        assert result.returncode == 2, args
        assert "Traceback" not in result.stderr


def test_output_cannot_overwrite_input(tmp_path: Path) -> None:

    path = tmp_path / "events.jsonl"
    text = json.dumps(get_data()) + "\n"
    path.write_text(text, encoding="utf-8")
    result = run_cli(
        tmp_path, "analyze", str(path), "--format", "jsonl", "--output", str(path)
    )

    assert result.returncode == 2
    assert path.read_text(encoding="utf-8") == text


def test_cli_filters(tmp_path: Path) -> None:
    path = tmp_path / "events.jsonl"
    data = get_data()
    data["level"] = "ERROR"
    path.write_text(json.dumps(data) + "\n", encoding="utf-8")
    result = run_cli(
        tmp_path,
        "analyze",
        str(path),
        "--format",
        "jsonl",
        "--start",
        "2026-10-24",
        "--level",
        "ERROR",
        "--source",
        "auth",
    )

    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["total_events"] == 1

    result = run_cli(
        tmp_path,
        "analyze",
        str(path),
        "--format",
        "jsonl",
        "--source",
        "auth",
        "--level",
        "ERROR",
    )

    assert result.returncode == 2
    assert "misplaced argument" in result.stderr
