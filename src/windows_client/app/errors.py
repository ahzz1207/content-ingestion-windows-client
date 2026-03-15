from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class ErrorDetails:
    code: str
    message: str
    stage: str
    details: dict[str, object] = field(default_factory=dict)


class WindowsClientError(Exception):
    """Structured application error for CLI and future GUI consumers."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        stage: str,
        details: dict[str, object] | None = None,
        cause: Exception | None = None,
    ) -> None:
        super().__init__(message)
        self.error = ErrorDetails(
            code=code,
            message=message,
            stage=stage,
            details=details or {},
        )
        self.__cause__ = cause

    @property
    def code(self) -> str:
        return self.error.code

    @property
    def message(self) -> str:
        return self.error.message

    @property
    def stage(self) -> str:
        return self.error.stage

    @property
    def details(self) -> dict[str, object]:
        return self.error.details
