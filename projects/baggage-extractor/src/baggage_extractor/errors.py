class ExtractionError(ValueError):
    """Base error raised when baggage extraction cannot produce a valid result."""


class InvalidExtractionInputError(ExtractionError):
    pass


class StructuredOutputParseError(ExtractionError):
    pass


class StructuredOutputValidationError(ExtractionError):
    pass
