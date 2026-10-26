from dataclasses import dataclass
from datetime import datetime
from streamstats.errors import InvalidEventError, InvalidTimestampError
@dataclass
class Event:
    timestamp:str
    level:str
    source:str
    message:str

def validation(data:dict )->Event:
    data = {k.strip(): v.strip() for k, v in data.items() if k is not None}
    required = ["timestamp", "level", "source", "message"]
    for field in required:
        if field not in data:
            raise InvalidEventError(f"Missing required field: {field}")

    if data["source"].strip() == '':
        raise InvalidEventError("Source cannot be empty")

    allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
    if data["level"] not in allowed:
        raise InvalidEventError(f"Invalid log level: {data['level']}")
    try:
        datetime.fromisoformat(data["timestamp"].replace("Z", "+00:00")) # Нулевое смещение
    except ValueError:
        raise InvalidTimestampError(f"Invalid timestamp format: {data['timestamp']}")

    return Event(
        timestamp=data["timestamp"],
        level=data["level"],
        source=data["source"],
        message=data["message"]
    )
