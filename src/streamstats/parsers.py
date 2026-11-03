import csv
import json
import time
from collections.abc import Callable, Iterable, Iterator
from pathlib import Path
from struct import Struct

from streamstats import models
from streamstats.errors import (
    InvalidEventError,
    InvalidTimestampError,
    StreamStatsError,
    UnsupportedFormatError,
    handle_record_error,
)
from streamstats.models import FIELDS, Event

BINARY_MAGIC = b"SSB1"
BINARY_HEADER = Struct("<IIII")
MAX_BINARY_PAYLOAD = 16 * 1024 * 1024


def stream_events(
    files: Iterable[str | Path],
    skip_invalid_flag: bool = False,
    format_name: str | None = None,
) -> Iterator[Event | str]:
    for file in files:
        file = str(file)
        format_files = format_name or Path(file).suffix.lstrip(".")

        if format_files == "bin":
            format_files = "binary"

        parser = get_parser(format_files)

        try:
            yield from parser(file, skip_invalid_flag)
        except (OSError, UnicodeError) as e:
            raise StreamStatsError(str(e), file=file) from e


def parse_text_lines(
    lines: Iterable[str],
    file: str,
    decode: Callable[[str], object],
    skip_invalid_flag: bool = False,
) -> Iterator[Event | str]:
    for line_number, line in enumerate(lines, start=1):
        clean_line = line.strip()

        if not clean_line:
            continue

        try:
            event = decode(clean_line)
            yield models.validation(event)
        except json.JSONDecodeError as e:
            yield handle_record_error(
                InvalidEventError(f"Invalid JSON: {e.msg}"),
                file,
                line_number,
                skip_invalid_flag,
            )
        except StreamStatsError as e:
            yield handle_record_error(e, file, line_number, skip_invalid_flag)


def parse_jsonl(file: str, skip_invalid_flag: bool = False) -> Iterator[Event | str]:
    with open(file, "r", encoding="utf-8-sig") as f:
        yield from parse_text_lines(f, file, json.loads, skip_invalid_flag)


def parse_csv(file: str, skip_invalid_flag: bool = False) -> Iterator[Event | str]:
    with open(file, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f, strict=True)

        try:
            cols = reader.fieldnames
        except csv.Error as e:
            raise InvalidEventError(str(e), file=file, line=1) from e

        if cols is None:
            return

        cols = [field.strip() for field in cols]

        if len(set(cols)) != len(cols) or not all(field in cols for field in FIELDS):
            raise InvalidEventError("Invalid CSV header", file=file, line=1)

        reader.fieldnames = cols

        while True:
            line_number = reader.line_num + 1

            try:
                row = next(reader)
            except StopIteration:
                return
            except csv.Error as e:
                yield handle_record_error(
                    InvalidEventError(str(e)), file, line_number, skip_invalid_flag
                )
                continue

            # Перенос в кавычках не начинает новую запись.
            line_number = reader.line_num

            for cell in row.values():
                if isinstance(cell, str):
                    line_number -= cell.count("\n")

            try:
                if None in row:
                    raise InvalidEventError("Too many CSV fields")

                yield models.validation(row)
            except StreamStatsError as e:
                yield handle_record_error(e, file, line_number, skip_invalid_flag)


def register_parser(name: str, parser: Callable) -> None:
    if not name or name in PARSERS:
        raise ValueError(f"Parser name is empty or already registered: {name}")

    PARSERS[name] = parser


def get_parser(name: str) -> Callable:
    if name not in PARSERS:
        raise UnsupportedFormatError(f"Unsupported format: {name}")

    return PARSERS[name]


def parse_binary(file: str, skip_invalid_flag: bool = False) -> Iterator[Event | str]:
    with open(file, "rb") as f:
        magic = f.read(len(BINARY_MAGIC))

        if not magic:
            return

        if magic != BINARY_MAGIC:
            raise InvalidEventError("Invalid binary signature SSB1", file, 1)

        line_number = 0

        while True:
            head = f.read(BINARY_HEADER.size)

            if not head:
                return

            line_number += 1

            try:
                if len(head) != BINARY_HEADER.size:
                    raise InvalidEventError("Truncated binary header")

                lens = BINARY_HEADER.unpack(head)
                row_size = sum(lens)

                if row_size > MAX_BINARY_PAYLOAD:
                    raise StreamStatsError(
                        "Binary record exceeds 16 MiB", file, line_number
                    )

                buf = memoryview(f.read(row_size))

                if len(buf) != row_size:
                    raise InvalidEventError("Truncated binary record")

                row = {}
                pos = 0

                for field, n in zip(FIELDS, lens, strict=True):
                    row[field] = str(buf[pos : pos + n], "utf-8")
                    pos += n

                yield models.validation(row)

            except UnicodeDecodeError as e:
                yield handle_record_error(
                    InvalidEventError(str(e)), file, line_number, skip_invalid_flag
                )
            except (InvalidEventError, InvalidTimestampError) as e:
                yield handle_record_error(e, file, line_number, skip_invalid_flag)


def follow_lines(file: str, poll_interval: float = 0.1) -> Iterator[str]:
    buffer = bytearray()

    with open(file, "rb") as f:
        while True:
            line = f.readline()

            if line:
                buffer.extend(line)

                # Без переноса строка пока не готова.
                if buffer.endswith(b"\n"):
                    clean_line = buffer.decode("utf-8-sig")
                    buffer.clear()
                    yield clean_line

                continue

            time.sleep(poll_interval)


PARSERS = {"csv": parse_csv, "jsonl": parse_jsonl, "binary": parse_binary}
