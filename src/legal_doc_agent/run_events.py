"""Structured generation run event storage."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from datetime import UTC, datetime
from threading import RLock
from typing import Any


def utc_timestamp() -> str:
    """Return an ISO-8601 UTC timestamp for run events."""

    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


@dataclass
class RunRecord:
    """Mutable generation run state."""

    run_id: str
    status: str = "running"
    events: list[dict[str, Any]] = field(default_factory=list)
    result: dict[str, Any] | None = None
    error: dict[str, Any] | None = None
    created_at: str = field(default_factory=utc_timestamp)
    updated_at: str = field(default_factory=utc_timestamp)


class RunStore:
    """In-memory run status store for local and warm serverless diagnostics."""

    def __init__(self, *, max_runs: int = 50) -> None:
        self._max_runs = max_runs
        self._records: dict[str, RunRecord] = {}
        self._order: list[str] = []
        self._lock = RLock()

    def start(self, run_id: str, *, message: str) -> None:
        with self._lock:
            record = RunRecord(run_id=run_id)
            self._records[run_id] = record
            self._order.append(run_id)
            self._trim()
            self.append(
                run_id,
                event_type="run_started",
                agent_id="planner",
                status="running",
                message=message,
            )

    def append(
        self,
        run_id: str,
        *,
        event_type: str,
        agent_id: str,
        status: str,
        message: str,
        data: dict[str, Any] | None = None,
    ) -> None:
        with self._lock:
            record = self._records.get(run_id)
            if record is None:
                return
            event = {
                "run_id": run_id,
                "event_id": f"{len(record.events) + 1:04d}",
                "type": event_type,
                "agent_id": agent_id,
                "status": status,
                "message": message,
                "at": utc_timestamp(),
            }
            if data:
                event["data"] = deepcopy(data)
            record.events.append(event)
            record.updated_at = event["at"]

    def complete(self, run_id: str, *, result: dict[str, Any], message: str) -> None:
        with self._lock:
            record = self._records.get(run_id)
            if record is None:
                return
            record.status = "completed"
            record.result = deepcopy(result)
            self.append(
                run_id,
                event_type="run_completed",
                agent_id="reviewer",
                status="completed",
                message=message,
            )

    def fail(self, run_id: str, *, error: str, message: str) -> None:
        with self._lock:
            record = self._records.get(run_id)
            if record is None:
                return
            record.status = "failed"
            record.error = {"error": error, "message": message}
            self.append(
                run_id,
                event_type="run_failed",
                agent_id="reviewer",
                status="failed",
                message=message,
                data={"error": error},
            )

    def get(self, run_id: str) -> dict[str, Any] | None:
        with self._lock:
            record = self._records.get(run_id)
            if record is None:
                return None
            return {
                "ok": True,
                "run_id": record.run_id,
                "status": record.status,
                "created_at": record.created_at,
                "updated_at": record.updated_at,
                "events": deepcopy(record.events),
                "result": deepcopy(record.result),
                "error": deepcopy(record.error),
            }

    def _trim(self) -> None:
        while len(self._order) > self._max_runs:
            oldest = self._order.pop(0)
            self._records.pop(oldest, None)
