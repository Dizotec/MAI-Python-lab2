import csv
import json
import logging
from pathlib import Path
from struct import pack

import pytest

from streamstats.analysis import statistics
from streamstats.errors import InvalidEventError, InvalidTimestampError
from streamstats.models import Event, validation
from streamstats.parsers import (
    follow_lines,
    parse_binary,
    stream_events,
)
from tests import get_data


def binary_row(data: dict[str, str]) -> bytes:
    row = [
        data[field].encode("utf-8")
        for field in ("timestamp", "level", "source", "message")
    ]
    return pack("<IIII", *(len(value) for value in row)) + b"".join(row)


def test_csv_and_jsonl(tmp_path: Path) -> None:
    data = get_data()
    data["message"] = 'Привет, "мир"!\nВторая строка'
    results = []

    for name in ["csv", "jsonl"]:
        path = tmp_path / f"events.{name}"

        with path.open("w", encoding="utf-8", newline="") as file:
            if name == "csv":
                writer = csv.DictWriter(file, fieldnames=list(data))
                writer.writeheader()
                writer.writerow(data)
            else:
                file.write(json.dumps(data, ensure_ascii=False) + "\n")

        original = path.read_bytes()
        event = next(stream_events([path]))

        assert isinstance(event, Event)
        assert event.message == data["message"]
        assert path.read_bytes() == original
        results.append(statistics(stream_events([path])))

    assert results[0] == results[1]


def test_empty_files(tmp_path: Path) -> None:
    for name in ["csv", "jsonl"]:
        path = tmp_path / f"empty.{name}"
        path.write_text("", encoding="utf-8")

        assert statistics(stream_events([path]))["total_count"] == 0


def test_bad_event_modes(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    data = get_data()
    bad = dict(data)
    bad["source"] = ""

    for name in ["csv", "jsonl"]:
        path = tmp_path / f"bad.{name}"

        with path.open("w", encoding="utf-8", newline="") as file:
            if name == "csv":
                writer = csv.DictWriter(file, fieldnames=list(data))
                writer.writeheader()
                writer.writerows([data, bad, data])
            else:
                for row in [data, bad, data]:
                    file.write(json.dumps(row) + "\n")

        events = stream_events([path])
        event = next(events)
        assert isinstance(event, Event)
        assert event.source == "auth"

        with pytest.raises(InvalidEventError) as error:
            next(events)

        assert error.value.file == str(path)
        assert error.value.line == (3 if name == "csv" else 2)

        caplog.clear()

        with caplog.at_level(logging.WARNING):
            result = statistics(stream_events([path], True))

        assert result["total_count"] == 2
        assert result["skipped_count"] == 1
        assert len(caplog.records) == 1
        assert caplog.records[0].levelno == logging.WARNING


def test_line_seven_and_lazy_reading(tmp_path: Path) -> None:
    path = tmp_path / "bad.jsonl"
    path.write_text(json.dumps(get_data()) + "\n" * 6 + "{broken}\n", encoding="utf-8")
    events = stream_events([path])

    event = next(events)
    assert isinstance(event, Event)
    assert event.source == "auth"

    with pytest.raises(InvalidEventError) as error:
        next(events)

    assert error.value.line == 7


def test_csv_multiline_error_location(tmp_path: Path) -> None:
    path = tmp_path / "bad.csv"
    path.write_text(
        "timestamp,level,source,message\n"
        '2026-10-24T10:00:00Z,INFO,auth,"line one\nline two"\n'
        "2026-10-24T10:00:00Z,ERROR,,bad\n",
        encoding="utf-8",
    )

    with pytest.raises(InvalidEventError) as error:
        list(stream_events([path]))

    assert error.value.line == 4


def test_invalid_timestamp_keeps_error_type(tmp_path: Path) -> None:
    data = get_data()
    data["timestamp"] = "bad date"
    path = tmp_path / "events.txt"
    path.write_text(json.dumps(data), encoding="utf-8")

    with pytest.raises(InvalidTimestampError) as error:
        list(stream_events([path], format_name="jsonl"))

    assert error.value.line == 1


def test_binary_event(tmp_path: Path) -> None:
    data = get_data()
    data["source"] = "сервис"
    data["message"] = "  Привет\nмир  "
    data["timestamp"] = "2026-10-24T10:00:00.123456+03:00"
    original = validation(data)
    path = tmp_path / "events.bin"
    path.write_bytes(b"SSB1" + binary_row(data))
    events = list(parse_binary(str(path)))

    assert len(events) == 1
    event = events[0]
    assert isinstance(event, Event)
    assert event.timestamp == original.timestamp
    assert event.source == original.source
    assert event.message == original.message


def test_binary_bad_record_and_truncation(tmp_path: Path) -> None:
    path = tmp_path / "bad.bin"
    good = tmp_path / "good.bin"
    good.write_bytes(b"SSB1" + binary_row(get_data()))
    data = get_data()
    data["level"] = "BAD"
    path.write_bytes(b"SSB1" + binary_row(data) + good.read_bytes()[4:])

    with pytest.raises(InvalidEventError):
        list(parse_binary(str(path)))

    result = statistics(parse_binary(str(path), True))
    assert result["total_count"] == 1
    assert result["skipped_count"] == 1

    path.write_bytes(good.read_bytes()[:-1])
    result = statistics(parse_binary(str(path), True))
    assert result["total_count"] == 0
    assert result["skipped_count"] == 1


def test_follow_appended_line_and_partial_utf8(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "live.jsonl"
    path.write_bytes(b"first\n")
    lines = follow_lines(str(path), poll_interval=0.01)
    assert next(lines) == "first\n"

    text = "Кириллица\n".encode()
    with path.open("ab") as file:
        file.write(text[:1])

    def append(interval: float) -> None:
        with path.open("ab") as file:
            file.write(text[1:])

    monkeypatch.setattr("streamstats.parsers.time.sleep", append)
    assert next(lines) == "Кириллица\n"


def test_follow_incomplete_line(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "live.jsonl"
    path.write_text(json.dumps(get_data()), encoding="utf-8")

    def stop(interval: float) -> None:
        raise KeyboardInterrupt

    monkeypatch.setattr("streamstats.parsers.time.sleep", stop)

    with pytest.raises(KeyboardInterrupt):
        next(follow_lines(str(path)))


def test_custom_parser_registry(tmp_path: Path) -> None:
    from collections.abc import Iterator

    from streamstats.models import Event
    from streamstats.parsers import PARSERS, parse_text_lines, register_parser

    def decode(line: str) -> dict[str, str]:
        values = line.rstrip("\r\n").split("|", 3)

        if len(values) != 4:
            raise InvalidEventError("Expected four fields")

        return dict(
            zip(("timestamp", "level", "source", "message"), values, strict=True)
        )

    def parse_pipe(filename: str, skip_invalid: bool = False) -> Iterator[Event | str]:
        with open(filename, encoding="utf-8") as file:
            yield from parse_text_lines(file, filename, decode, skip_invalid)

    path = tmp_path / "custom.txt"
    path.write_text("2026-10-24T10:00:00Z|ERROR|сервис|Ошибка\n", encoding="utf-8")
    register_parser("pipe", parse_pipe)

    try:
        result = statistics(stream_events([path], format_name="pipe"))
        assert result["source_counts"] == {"сервис": 1}
    finally:
        PARSERS.pop("pipe")
