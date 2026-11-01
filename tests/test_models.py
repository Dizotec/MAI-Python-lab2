import pytest

from streamstats.errors import InvalidEventError, InvalidTimestampError
from streamstats.models import validation


@pytest.mark.parametrize("field", ["timestamp", "level", "source", "message"])
def test_missing_field(data: dict[str, str], field: str) -> None:
    """Обязательные поля нельзя пропускать."""
    del data[field]
    with pytest.raises(InvalidEventError, match=field):
        validation(data)


def test_invalid_date(data: dict[str, str]) -> None:
    """Для неверной даты используется отдельное исключение."""
    data["timestamp"] = "2026-02-30T10:00:00Z"
    with pytest.raises(InvalidTimestampError):
        validation(data)
