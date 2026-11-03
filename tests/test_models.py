from datetime import UTC

import pytest

from streamstats.errors import InvalidEventError, InvalidTimestampError
from streamstats.models import validation
from tests import get_data


def test_missing_field() -> None:

    for field in ["timestamp", "level", "source", "message"]:
        data = get_data()
        del data[field]

        with pytest.raises(InvalidEventError, match=field):
            validation(data)


def test_wrong_types() -> None:

    wrong_events: list[object] = [None, [], 42, "text"]

    wrong_values: list[object] = [None, 42, [], {}]

    for data in wrong_events:
        with pytest.raises(InvalidEventError):
            validation(data)

    for field in ["timestamp", "level", "source", "message"]:
        for value in wrong_values:
            row: dict[str, object] = dict(get_data())
            row[field] = value

            with pytest.raises(InvalidEventError, match=field):
                validation(row)


def test_invalid_values() -> None:
    for field, value in [("source", "  "), ("level", "BAD")]:
        data = get_data()
        data[field] = value

        with pytest.raises(InvalidEventError):
            validation(data)

    data = get_data()
    data["timestamp"] = "2026-02-30T10:00:00Z"

    with pytest.raises(InvalidTimestampError, match="timestamp"):
        validation(data)


def test_timezone_and_message() -> None:
    data = get_data()
    data["timestamp"] = "2026-10-24T10:00:00+03:00"
    data["message"] = "  Привет  "
    event = validation(data)

    assert event.timestamp.hour == 7
    assert event.timestamp.tzinfo == UTC
    assert event.message == "  Привет  "

    data["timestamp"] = "2026-10-24"
    assert validation(data).timestamp.tzinfo == UTC
