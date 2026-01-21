"""Exception classes for the llmops SDK."""


class ConfigurationError(Exception):
    """Raised when SDK configuration is invalid.

    This exception is only raised during init() when configuration
    is invalid in strict validation mode. In permissive mode,
    configuration errors result in a no-op tracer provider instead.
    """
