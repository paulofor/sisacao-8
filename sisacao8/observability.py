"""Utilities that keep Sisacao-8 jobs observable in production."""

from __future__ import annotations

import datetime as dt
import json
import logging
import uuid
from typing import Any, Dict, Mapping, MutableMapping


def _normalize_value(value: Any) -> Any:
    """Return ``value`` encoded into JSON-friendly objects."""

    if isinstance(value, (dt.datetime, dt.date)):
        return value.isoformat()
    if isinstance(value, set):
        return sorted(value)
    if isinstance(value, tuple):
        return [_normalize_value(item) for item in value]
    return value


class StructuredLogger:
    """Emit JSON logs with a consistent schema."""

    def __init__(
        self,
        job_name: str,
        *,
        logger: logging.Logger | None = None,
        run_id: str | None = None,
        context: Mapping[str, Any] | None = None,
    ) -> None:
        self.logger = logger or logging.getLogger(job_name)
        self.job_name = job_name
        self.run_id = run_id or uuid.uuid4().hex
        self._context: MutableMapping[str, Any] = {
            "job_name": job_name,
            "run_id": self.run_id,
        }
        if context:
            self.update_context(**context)

    def update_context(self, **fields: Any) -> None:
        """Augment the base payload for every subsequent log."""

        for key, value in fields.items():
            if value is None:
                continue
            self._context[key] = _normalize_value(value)

    def _build_payload(self, status: str, message: str, **fields: Any) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "timestamp": dt.datetime.now(dt.timezone.utc).isoformat(),
            **self._context,
            "status": status.upper(),
            "message": message,
        }
        for key, value in fields.items():
            if value is None:
                continue
            payload[key] = _normalize_value(value)
        return payload

    def log(
        self,
        status: str,
        message: str,
        *,
        level: int = logging.INFO,
        **fields: Any,
    ) -> Dict[str, Any]:
        """Emit one structured log line and return the payload."""

        payload = self._build_payload(status, message, **fields)
        self.logger.log(level, json.dumps(payload, ensure_ascii=False))
        return payload

    def started(self, **fields: Any) -> Dict[str, Any]:
        return self.log("STARTED", "Job started", **fields)

    def ok(self, message: str, **fields: Any) -> Dict[str, Any]:
        return self.log("OK", message, **fields)

    def warn(self, message: str, **fields: Any) -> Dict[str, Any]:
        return self.log("WARN", message, level=logging.WARNING, **fields)

    def error(self, message: str, **fields: Any) -> Dict[str, Any]:
        return self.log("ERROR", message, level=logging.ERROR, **fields)

    def exception(self, error: BaseException, **fields: Any) -> Dict[str, Any]:
        details = {
            "error_type": error.__class__.__name__,
            "error_message": str(error),
        }
        cause = getattr(error, "__cause__", None)
        if cause is not None:
            details["cause"] = f"{cause.__class__.__name__}: {cause}"
        merged_fields = {**fields, "exception": details}
        return self.log("ERROR", "Unhandled exception", level=logging.ERROR, **merged_fields)
