from __future__ import annotations

import asyncio
from datetime import date
from typing import Any

import pytest

from agent.cases import InvalidTransition, transition
from agent.loop import resolve_disruption
from agent.ranker import Itinerary


class FakeTools:
    def __init__(self, script: list[dict[str, Any]]) -> None:
        self.script = list(script)
        self.calls: list[tuple[str, dict[str, Any]]] = []

    async def call(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        self.calls.append((name, arguments))
        if not self.script:
            return {"reason_code": "OK", "decision": "allow"}
        return self.script.pop(0)


def _itin(identifier: str, fare: int, delay: int = 40, arrival: date = date(2026, 10, 8)) -> Itinerary:
    return Itinerary(identifier, identifier, delay, fare, 0, 80, "economy", arrival, identifier)


def test_confirmed_rebook_does_not_call_hotel_on_the_same_day() -> None:
    tools = FakeTools([{"reason_code": "OK"}, {"reason_code": "OK"}])
    log = asyncio.run(resolve_disruption(tools, [_itin("best", 18_000)], "case-1", "cancellation"))
    assert log.state == "Confirmed"
    assert [name for name, _ in tools.calls] == ["rebook_flight", "send_notification"]


def test_cap_deny_tries_the_next_itinerary() -> None:
    tools = FakeTools([{"reason_code": "AGENT_CAP"}, {"reason_code": "OK"}, {"reason_code": "OK"}])
    inventory = [_itin("expensive", 50_000, delay=10), _itin("cheaper", 9_000, delay=20)]
    log = asyncio.run(resolve_disruption(tools, inventory, "case-2", "cancellation"))
    assert log.state == "Confirmed"
    rebooks = [arguments["itinerary_id"] for name, arguments in tools.calls if name == "rebook_flight"]
    assert rebooks == ["expensive", "cheaper"]


def test_emergency_stop_does_not_try_another_flight() -> None:
    tools = FakeTools([{"reason_code": "EMERGENCY_STOP"}])
    inventory = [_itin("a", 18_000, delay=10), _itin("b", 9_000, delay=20)]
    log = asyncio.run(resolve_disruption(tools, inventory, "case-3", "cancellation"))
    assert log.state == "Blocked"
    assert [name for name, _ in tools.calls] == ["rebook_flight"]


def test_hotel_is_skipped_when_the_arrival_date_is_unchanged() -> None:
    tools = FakeTools([{"reason_code": "OK"}, {"reason_code": "OK"}])
    log = asyncio.run(resolve_disruption(tools, [_itin("same-day", 18_000)], "case-4", "cancellation"))
    assert "change_hotel" not in [name for name, _ in tools.calls]
    assert log.state == "Confirmed"


def test_hotel_deny_keeps_the_flight() -> None:
    tools = FakeTools([{"reason_code": "OK"}, {"reason_code": "AGENT_CAP"}, {"reason_code": "OK"}])
    inventory = [_itin("next", 18_000, delay=320, arrival=date(2026, 10, 9))]
    log = asyncio.run(resolve_disruption(tools, inventory, "case-5", "cancellation"))
    assert log.state == "Confirmed"
    assert any(event["event"] == "hotel_deny" and event["detail"]["flight_kept"] for event in log.events)
    assert [name for name, _ in tools.calls] == ["rebook_flight", "change_hotel", "send_notification"]


def test_illegal_transition_raises() -> None:
    with pytest.raises(InvalidTransition):
        transition("Watching", "adapter_ok")
