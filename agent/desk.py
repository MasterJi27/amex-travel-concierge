from __future__ import annotations

from typing import Any

DEFAULT_MAX_FARE_CENTS = 100_000


class BookingDesk:
    """Books flights, hotels, and notices inside the concierge. No other service is involved."""

    def __init__(self, max_fare_cents: int = DEFAULT_MAX_FARE_CENTS) -> None:
        self.caps: dict[str, int] = {}
        self.default_cap = max_fare_cents
        self.flight_attempts = 0
        self.flight_committed = 0
        self._results: dict[str, dict[str, Any]] = {}

    def cap_for(self, trip_id: str) -> int:
        return self.caps.get(trip_id, self.default_cap)

    def set_cap(self, trip_id: str, max_fare_cents: int) -> int:
        if max_fare_cents < 0:
            raise ValueError("cap must be >= 0")
        self.caps[trip_id] = max_fare_cents
        return max_fare_cents

    def reset(self) -> None:
        self.caps.clear()
        self.default_cap = DEFAULT_MAX_FARE_CENTS
        self.flight_attempts = 0
        self.flight_committed = 0
        self._results.clear()

    async def call(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        key = str(arguments["idempotency_key"])
        cached = self._results.get(key)
        if cached is not None:
            return cached
        trip_id = str(arguments.get("trip_id", "trip-2401"))
        if name == "rebook_flight":
            result = self._rebook(trip_id, int(arguments["fare_delta_cents"]))
        elif name == "change_hotel":
            result = {"decision": "allow", "reason_code": "OK"}
        elif name == "send_notification":
            result = {"decision": "allow", "reason_code": "OK"}
        else:
            result = {"decision": "deny", "reason_code": "ACTION_NOT_ALLOWED"}
        self._results[key] = result
        return result

    def _rebook(self, trip_id: str, fare_delta_cents: int) -> dict[str, Any]:
        self.flight_attempts += 1
        if fare_delta_cents > self.cap_for(trip_id):
            return {"decision": "deny", "reason_code": "AGENT_CAP"}
        self.flight_committed += 1
        return {"decision": "allow", "reason_code": "OK"}
