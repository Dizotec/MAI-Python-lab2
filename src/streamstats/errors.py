class StreamStatsError(Exception):
    def __init__(self, message, file=None, line=None):
        super().__init__(message)
        self.file = file
        self.line = line

class UnsupportedFormatError(StreamStatsError):
    """Вызывается, если указан формат, отличный от csv или jsonl."""
    pass

class InvalidEventError(StreamStatsError):
    """Вызывается при отсутствии обязательных полей или пустом source."""
    pass

class InvalidTimestampError(StreamStatsError):
    """Вызывается, если временная метка не соответствует ISO 8601."""
    pass

class CLIConfigurationError(StreamStatsError):
    """Вызывается при ошибках в переданных аргументах командной строки."""
    pass
