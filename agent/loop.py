from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from typing import Any, Protocol

from agent.cases import CAP_REASONS, reason_text, transition
from agent.ranker import HOTEL_NIGHT_CENTS, ORIGINAL_ARRIVAL, Itinerary, as_public, hotel_nights, legal_itineraries

Sink = Callable[[dict[str, Any]], Awaitable[None]]


class ToolClient(Protocol):
    async def call(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]: ...


class CaseLog:
    def __init__(self) -> None:
        self.state = "Watching"
        self.events: list[dict[str, Any]] = []

    def apply(self, event: str, detail: dict[str, Any]) -> None:
        self.state = transition(self.state, event)
        self.events.append({"state": self.state, "event": event, "detail": detail})


async def _emit(case: CaseLog, event: str, detail: dict[str, Any], sink: Sink | None) -> None:
    case.apply(event, detail)
    if sink is not None:
        await sink(case.events[-1])


async def resolve_disruption(
    tools: ToolClient,
    inventory: list[Itinerary],
    case_id: str,
    kind: str,
    log: CaseLog | None = None,
    sink: Sink | None = None,
    trip_id: str = "trip-2401",
    member_name: str = "Ananya",
    inbound_flight: str = "AI111",
) -> CaseLog:
    case = log or CaseLog()
    await _emit(case, "disruption", {"kind": kind}, sink)
    ranked = legal_itineraries(inventory)
    shown = ranked[:3]
    await _emit(case, "plan", {"options": [as_public(row) for row in shown]}, sink)
    if not ranked:
        await _emit(case, "no_candidate", {}, sink)
        return case

    chosen: Itinerary | None = None
    last_reason = "AGENT_CAP"
    for itinerary in shown:
        await _emit(
            case,
            "candidate_chosen",
            {"itinerary_id": itinerary.id, "summary": itinerary.summary, "fare_delta_cents": itinerary.fare_delta_cents},
            sink,
        )
        result = await tools.call(
            "rebook_flight",
            {
                "agent_id": "travel-concierge",
                "trip_id": trip_id,
                "idempotency_key": f"{case_id}:rebook:{itinerary.flight_numbers}",
                "fare_delta_cents": itinerary.fare_delta_cents,
                "itinerary_id": itinerary.id,
                "flight_numbers": itinerary.flight_numbers,
            },
        )
        reason = str(result["reason_code"])
        last_reason = reason
        if reason == "OK":
            await _emit(case, "authorize_allow", {"itinerary_id": itinerary.id}, sink)
            await _emit(case, "adapter_ok", {"itinerary_id": itinerary.id, "text": reason_text("OK")}, sink)
            chosen = itinerary
            break
        if reason == "ADAPTER_FAILED":
            await _emit(case, "authorize_allow", {"itinerary_id": itinerary.id}, sink)
            await _emit(case, "adapter_error", {"text": reason_text(reason)}, sink)
            return case
        if reason in CAP_REASONS:
            await _emit(
                case,
                "cap_denied",
                {"itinerary_id": itinerary.id, "reason_code": reason, "text": reason_text(reason)},
                sink,
            )
            continue
        await _emit(case, "authorize_deny", {"itinerary_id": itinerary.id, "reason_code": reason, "text": reason_text(reason)}, sink)
        return case

    if chosen is None:
        await _emit(case, "no_candidate", {"reason_code": last_reason, "text": reason_text(last_reason)}, sink)
        return case

    nights = hotel_nights(chosen.arrival_date, ORIGINAL_ARRIVAL)
    if nights > 0:
        await _emit(case, "hotel_chosen", {"nights": nights}, sink)
        hotel = await tools.call(
            "change_hotel",
            {
                "agent_id": "travel-concierge",
                "trip_id": trip_id,
                "idempotency_key": f"{case_id}:hotel",
                "amount_cents": nights * HOTEL_NIGHT_CENTS,
                "nights": nights,
            },
        )
        hotel_reason = str(hotel["reason_code"])
        if hotel_reason == "OK":
            await _emit(case, "authorize_allow", {"nights": nights}, sink)
            await _emit(case, "adapter_ok", {"nights": nights, "text": "Hotel extended."}, sink)
        else:
            await _emit(
                case,
                "hotel_deny",
                {"reason_code": hotel_reason, "text": reason_text(hotel_reason), "flight_kept": True},
                sink,
            )

    note = await tools.call(
        "send_notification",
        {
            "agent_id": "travel-concierge",
            "trip_id": trip_id,
            "idempotency_key": f"{case_id}:notify",
            "message": _member_message(kind, chosen, member_name, inbound_flight),
        },
    )
    note_reason = str(note["reason_code"])
    if note_reason == "OK":
        await _emit(case, "notified", {"message": _member_message(kind, chosen, member_name, inbound_flight)}, sink)
    else:
        await _emit(case, "notify_denied", {"reason_code": note_reason, "text": reason_text(note_reason)}, sink)
    return case


def _member_message(kind: str, chosen: Itinerary, name: str = "Ananya", inbound: str = "AI111") -> str:
    fare = f"₹{chosen.fare_delta_cents:,}"
    if kind == "missed_connection":
        lead = f"{name}, {inbound} late hai. Agla connection nahi banta."
    else:
        lead = f"{name}, {inbound} cancel ho gaya."
    hotel = "Hotel same rahega." if chosen.arrival_date == ORIGINAL_ARRIVAL else "Hotel ek raat extend ho gaya."
    return f"{lead} {chosen.flight_numbers} confirm hai, extra fare {fare}. {hotel}"


def event_payload(event: dict[str, Any]) -> str:
    return json.dumps(event["detail"], sort_keys=True)
