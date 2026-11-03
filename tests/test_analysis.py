import csv
import json
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path

import pytest

from streamstats.analysis import filter_events, memory_benchmark, statistics
from streamstats.models import Event, parse_timestamp, validation
from streamstats.report import create_report
from tests import get_data


def test_counts_and_time_bounds() -> None:
    events = []

    for time, level in [("10:20", "INFO"), ("10:00", "ERROR"), ("10:10", "CRITICAL")]:
        row = get_data()
        row["timestamp"] = f"2026-10-24T{time}:00Z"
        row["level"] = level
        events.append(validation(row))

    result = statistics(iter(events))

    assert result["total_count"] == 3
    assert result["level_counts"] == {"INFO": 1, "ERROR": 1, "CRITICAL": 1}
    assert result["source_counts"] == {"auth": 3}
    assert result["top_5_sources"] == [("auth", 2)]
    assert result["first_timestamp"] == datetime.fromisoformat(
        "2026-10-24T10:00:00+00:00"
    )
    assert result["last_timestamp"] == datetime.fromisoformat(
        "2026-10-24T10:20:00+00:00"
    )


def test_top_order_and_limit() -> None:
    events = []

    for source in ["f", "e", "d", "c", "b", "a", "f"]:
        row = get_data()
        row["source"] = source
        row["level"] = "ERROR"
        events.append(validation(row))

    assert statistics(iter(events))["top_5_sources"] == [
        ("f", 2),
        ("a", 1),
        ("b", 1),
        ("c", 1),
        ("d", 1),
    ]
    assert statistics(iter(events), top_n=2)["top_5_sources"] == [("f", 2), ("a", 1)]


def test_empty_and_skipped() -> None:
    result = statistics(iter(()))

    assert result["total_count"] == 0
    assert result["source_counts"] == {}
    assert result["first_timestamp"] is None
    assert result["last_timestamp"] is None

    result = statistics(iter(["SKIP"]))

    assert result["skipped_count"] == 1
    assert result["total_count"] == 0


def test_follow_interrupt_keeps_statistics() -> None:
    def source() -> Iterator[Event]:
        yield validation(get_data())
        raise KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
        statistics(source())

    result = statistics(source(), follow_flag=True)

    assert result["total_count"] == 1
    assert result["source_counts"] == {"auth": 1}


def test_filters_are_lazy() -> None:
    data = get_data()

    def source() -> Iterator[Event]:
        yield validation(data)
        raise AssertionError("Read ahead")

    events = filter_events(source(), start=parse_timestamp(data["timestamp"]))
    event = next(events)
    assert isinstance(event, Event)
    assert event.source == "auth"


def test_filters_and_skipped_records() -> None:
    events = []

    for level in ["INFO", "ERROR", "CRITICAL"]:
        data = get_data()
        data["level"] = level
        events.append(validation(data))

    items: list[Event | str] = ["SKIP", *events]
    stream = iter(items)
    filtered = filter_events(
        stream,
        start=parse_timestamp("2026-10-24T10:00:00Z"),
        end=parse_timestamp("2026-10-24T10:00:00Z"),
        level="ERROR",
        source="auth",
    )
    result = statistics(filtered)

    assert result["total_count"] == 1
    assert result["level_counts"] == {"ERROR": 1}
    assert result["skipped_count"] == 1
    assert list(filter_events(events, source="other")) == []
    assert list(filter_events(events, end=parse_timestamp("2026-10-23"))) == []


def test_csv_report(tmp_path: Path) -> None:
    path = tmp_path / "report.csv"
    stats = statistics(iter([validation(get_data())]))
    create_report(stats, path, "csv")

    with path.open(encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))

    assert {"section": "summary", "name": "total_events", "value": "1"} in rows
    assert {"section": "sources", "name": "auth", "value": "1"} in rows


def test_memory_benchmark(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)
    memory_benchmark(1)
    data = json.loads(capsys.readouterr().out)

    assert data["file_bytes"] >= 1024 * 1024
    assert data["events"] > 0
    assert data["python_peak_bytes"] > 0
    assert list(tmp_path.iterdir()) == []
