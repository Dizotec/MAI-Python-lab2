import json
import tempfile
import time
import tracemalloc
from collections.abc import Iterable, Iterator
from datetime import datetime
from pathlib import Path

from streamstats.models import Event


def statistics(
    events: Iterable[Event | str],
    skip_invalid_flag: bool = False,
    top_n: int = 5,
    follow_flag: bool = False,
) -> dict:
    event_count = 0
    level_count: dict[str, int] = {}
    errors_source_count: dict[str, int] = {}
    f_timestamp = None
    l_timestamp = None
    skipped_count = 0
    source_count: dict[str, int] = {}

    try:
        for i in events:
            if isinstance(i, str):
                skipped_count += 1
                continue

            event_count += 1
            source_count[i.source] = source_count.get(i.source, 0) + 1
            level_count[i.level] = level_count.get(i.level, 0) + 1

            if i.level in ("ERROR", "CRITICAL"):
                errors_source_count[i.source] = errors_source_count.get(i.source, 0) + 1

            if f_timestamp is None or f_timestamp > i.timestamp:
                f_timestamp = i.timestamp

            if l_timestamp is None or l_timestamp < i.timestamp:
                l_timestamp = i.timestamp

    except KeyboardInterrupt:
        if not follow_flag:
            raise

    sorted_errors = sorted(errors_source_count.items(), key=lambda x: (-x[1], x[0]))

    top_5_errors = sorted_errors[:top_n]

    return {
        "total_count": event_count,
        "level_counts": level_count,
        "top_5_sources": top_5_errors,
        "first_timestamp": f_timestamp,
        "last_timestamp": l_timestamp,
        "skipped_count": skipped_count,
        "source_counts": source_count,
        "skip_invalid_flag": skip_invalid_flag,
    }


def filter_events(
    events: Iterable[Event | str],
    start: datetime | None = None,
    end: datetime | None = None,
    level: str | None = None,
    source: str | None = None,
) -> Iterator[Event | str]:
    for i in events:
        # SKIP нужен счётчику.
        if isinstance(i, str):
            yield i
            continue

        if start is not None and i.timestamp < start:
            continue

        if end is not None and i.timestamp > end:
            continue

        if level is not None and i.level != level:
            continue

        if source is not None and i.source != source:
            continue

        yield i


def memory_benchmark(size: int = 500) -> None:
    from streamstats.parsers import stream_events

    sample = {
        "timestamp": "2026-10-24T10:00:00Z",
        "level": "INFO",
        "source": "auth",
        "message": "x" * 850,
    }
    log_line = (json.dumps(sample) + "\n").encode("utf-8")
    left = (size * 1024 * 1024 + len(log_line) - 1) // len(log_line)

    with tempfile.NamedTemporaryFile(
        dir=Path.cwd(), suffix=".jsonl", delete=False
    ) as f:
        tmp_file = Path(f.name)

    try:
        with tmp_file.open("wb") as f:
            while left:
                n = min(left, 1024)
                f.write(log_line * n)
                left -= n

        tracemalloc.start()
        timer = time.perf_counter()
        counts = statistics(stream_events([tmp_file], format_name="jsonl"))
        spent = time.perf_counter() - timer
        _, peak_mem = tracemalloc.get_traced_memory()

        print(
            json.dumps(
                {
                    "file_bytes": tmp_file.stat().st_size,
                    "events": counts["total_count"],
                    "python_peak_bytes": peak_mem,
                    "seconds": round(spent, 3),
                },
                indent=2,
            )
        )

    finally:
        tracemalloc.stop()
        tmp_file.unlink(missing_ok=True)


if __name__ == "__main__":
    memory_benchmark()
