"""Application-specific exceptions."""


class ReportDesktopError(Exception):
    """Base exception for the desktop app."""


class ValidationFailed(ReportDesktopError):
    """Validation blocked further processing."""


class ReportGenerationFailed(ReportDesktopError):
    """Report pipeline or Excel export failed."""
