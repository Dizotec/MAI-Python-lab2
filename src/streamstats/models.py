from dataclasses import dataclass
from datetime import UTC, datetime

from streamstats.errors import InvalidEventError, InvalidTimestampError

FIELDS = ("timestamp", "level", "source", "message")
LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")


@dataclass
class Event:
    timestamp: datetime
    level: str
    source: str
    message: str


def validation(data: object) -> Event:
    if not isinstance(data, dict):
        raise InvalidEventError("Event must be dictionary")

    for field in FIELDS:
        if field not in data:
            raise InvalidEventError(f"Missing required field: {field}")

        if not isinstance(data[field], str):
            raise InvalidEventError(f"Field {field} must be a string")

    if data["source"].strip() == "":
        raise InvalidEventError("Source cannot be empty")

    if data["level"] not in LEVELS:
        raise InvalidEventError(f"Invalid log level: {data['level']}")

    time = parse_timestamp(data["timestamp"])

    return Event(
        timestamp=time,
        level=data["level"],
        source=data["source"].strip(),
        message=data["message"],
    )


def parse_timestamp(value: str) -> datetime:
    try:
        time = datetime.fromisoformat(value)

        if time.tzinfo is None:
            time = time.replace(tzinfo=UTC)

        return time.astimezone(UTC)
    except (ValueError, OverflowError) as e:
        raise InvalidTimestampError(f"Invalid timestamp format: {value}") from e
