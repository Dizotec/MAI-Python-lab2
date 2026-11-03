import logging

logger = logging.getLogger(__name__)


class StreamStatsError(Exception):
    def __init__(
        self, message: str, file: str | None = None, line: int | None = None
    ) -> None:
        super().__init__(message)
        self.file = file
        self.line = line


class UnsupportedFormatError(StreamStatsError):
    pass


class InvalidEventError(StreamStatsError):
    pass


class InvalidTimestampError(StreamStatsError):
    pass


class CLIConfigurationError(StreamStatsError):
    pass


def handle_record_error(
    e: StreamStatsError, file: str, line: int, skip_invalid_flag: bool
) -> str:
    e.file = file
    e.line = line

    if not skip_invalid_flag:
        raise e

    logger.warning("%s:%d: %s", file, line, e)

    return "SKIP"
