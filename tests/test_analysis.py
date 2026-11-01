from datetime import datetime

from streamstats.analysis import statistics
from streamstats.models import validation


def test_counts_and_time_bounds(data: dict[str, str]) -> None:
    """Счётчики и границы времени не зависят от порядка событий."""
    events = []
    for time, level in [("10:20", "INFO"), ("10:00", "ERROR"), ("10:10", "CRITICAL")]:
        row = dict(data)
        row["timestamp"] = f"2026-10-24T{time}:00Z"
        row["level"] = level
        events.append(validation(row))
    result = statistics(iter(events), False)
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


def test_top_five_order(data: dict[str, str]) -> None:
    """При равном числе ошибок источники сортируются по имени."""
    events = []
    for source in ["f", "e", "d", "c", "b", "a", "f"]:
        row = dict(data)
        row["source"] = source
        row["level"] = "ERROR"
        events.append(validation(row))
    result = statistics(iter(events), False)
    assert result["top_5_sources"] == [("f", 2), ("a", 1), ("b", 1), ("c", 1), ("d", 1)]
