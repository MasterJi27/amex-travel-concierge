from __future__ import annotations

from datetime import datetime, timezone

from agent.detector import Segment
from agent.ranker import DEMO_INVENTORY, INVENTORY_2402, INVENTORY_2403, Itinerary

TRIP_ID = "trip-2401"
MEMBER_ID = "cm-10442"
SEED_VERSION = 4

PASSENGER = {
    "name": "Ananya Sharma",
    "member_id": MEMBER_ID,
    "card": "Platinum Travel",
    "last4": "4429",
    "pnr": "K7H2QD",
    "ticket": "098 2148 831046",
    "passport": "Indian",
    "phone": "+91 98100 44128",
    "transit": "UK airside transit covered by the US B1/B2 on file",
}

HOTEL = {
    "city": "New York",
    "name": "Hilton Garden Inn Times Square",
    "address": "35 W 36th St, Manhattan",
    "checkin": "2026-10-08",
    "checkout": "2026-10-09",
    "nights": 1,
    "nightly_cents": 24000,
    "confirmation": "HGI-88421",
    "room": "King, late checkout held",
}


def seed_segments() -> list[Segment]:
    return [
        Segment(
            "ua410",
            "AI111",
            "DEL",
            "LHR",
            datetime(2026, 10, 8, 3, 0, tzinfo=timezone.utc),
            datetime(2026, 10, 8, 12, 30, tzinfo=timezone.utc),
            terminal_origin="T3",
            terminal_destination="T2",
            airline="Air India",
            aircraft="Boeing 787-8",
            seat="14C",
            cabin="Economy",
        ),
        Segment(
            "ua882",
            "BA173",
            "LHR",
            "JFK",
            datetime(2026, 10, 8, 14, 5, tzinfo=timezone.utc),
            datetime(2026, 10, 8, 22, 15, tzinfo=timezone.utc),
            terminal_origin="T5",
            terminal_destination="T8",
            airline="British Airways",
            aircraft="Airbus A350-1000",
            seat="22A",
            cabin="Economy",
        ),
    ]


PASSENGER_2402 = {
    "name": "Rohan Mehta",
    "member_id": "cm-20771",
    "card": "Platinum Travel",
    "last4": "8810",
    "pnr": "M4R2TB",
    "ticket": "098 7751 209844",
    "passport": "Indian",
    "phone": "+91 98200 77102",
    "transit": "US B1/B2 on file",
}

HOTEL_2402 = {
    "city": "Chicago",
    "name": "Hyatt Regency O'Hare",
    "address": "Rosemont, near ORD",
    "checkin": "2026-10-08",
    "checkout": "2026-10-09",
    "nights": 1,
    "nightly_cents": 24000,
    "confirmation": "HAY-55210",
    "room": "King",
}

PASSENGER_2403 = {
    "name": "Priya Nair",
    "member_id": "cm-30918",
    "card": "Platinum Travel",
    "last4": "3356",
    "pnr": "P9T4SL",
    "ticket": "098 3309 184422",
    "passport": "Indian",
    "phone": "+91 98840 30918",
    "transit": "US B1/B2 on file",
}

HOTEL_2403 = {
    "city": "San Francisco",
    "name": "Courtyard SFO Downtown",
    "address": "299 2nd St",
    "checkin": "2026-10-08",
    "checkout": "2026-10-09",
    "nights": 1,
    "nightly_cents": 24000,
    "confirmation": "CY-77120",
    "room": "Queen",
}


def seed_segments_2402() -> list[Segment]:
    return [
        Segment(
            "lh756",
            "LH756",
            "BOM",
            "FRA",
            datetime(2026, 10, 8, 0, 30, tzinfo=timezone.utc),
            datetime(2026, 10, 8, 9, 0, tzinfo=timezone.utc),
            terminal_origin="T2",
            terminal_destination="T1",
            airline="Lufthansa",
            aircraft="Airbus A350",
            seat="21K",
            cabin="Economy",
        ),
        Segment(
            "lh402",
            "LH402",
            "FRA",
            "ORD",
            datetime(2026, 10, 8, 10, 35, tzinfo=timezone.utc),
            datetime(2026, 10, 8, 18, 35, tzinfo=timezone.utc),
            terminal_origin="T1",
            terminal_destination="T5",
            airline="Lufthansa",
            aircraft="Airbus A340",
            seat="30C",
            cabin="Economy",
        ),
    ]


def seed_segments_2403() -> list[Segment]:
    return [
        Segment(
            "ai111b",
            "AI111",
            "DEL",
            "LHR",
            datetime(2026, 10, 8, 3, 0, tzinfo=timezone.utc),
            datetime(2026, 10, 8, 12, 30, tzinfo=timezone.utc),
            terminal_origin="T3",
            terminal_destination="T2",
            airline="Air India",
            aircraft="Boeing 787-8",
            seat="18A",
            cabin="Economy",
        ),
        Segment(
            "ba285",
            "BA285",
            "LHR",
            "SFO",
            datetime(2026, 10, 8, 14, 5, tzinfo=timezone.utc),
            datetime(2026, 10, 8, 22, 15, tzinfo=timezone.utc),
            terminal_origin="T5",
            terminal_destination="INTL",
            airline="British Airways",
            aircraft="Airbus A380",
            seat="31K",
            cabin="Economy",
        ),
    ]


TRIPS: dict[str, dict[str, object]] = {
    "trip-2401": {"member_id": MEMBER_ID, "passenger": PASSENGER, "hotel": HOTEL},
    "trip-2402": {"member_id": "cm-20771", "passenger": PASSENGER_2402, "hotel": HOTEL_2402},
    "trip-2403": {"member_id": "cm-30918", "passenger": PASSENGER_2403, "hotel": HOTEL_2403},
}

TRIP_INVENTORIES: dict[str, list[Itinerary]] = {
    "trip-2401": DEMO_INVENTORY,
    "trip-2402": INVENTORY_2402,
    "trip-2403": INVENTORY_2403,
}

_SEED_FNS = {
    "trip-2401": seed_segments,
    "trip-2402": seed_segments_2402,
    "trip-2403": seed_segments_2403,
}


def seed_segments_for(trip_id: str) -> list[Segment]:
    try:
        return _SEED_FNS[trip_id]()
    except KeyError:
        raise KeyError(f"unknown trip {trip_id}") from None


def route_summary(trip_id: str) -> str:
    segments = seed_segments_for(trip_id)
    first, last = segments[0], segments[-1]
    via = " → ".join(sorted({segment.destination for segment in segments[:-1]}))
    return f"{first.origin} → {via} → {last.destination}"


def segment_to_dict(segment: Segment) -> dict[str, str]:
    return {
        "id": segment.id,
        "flight_number": segment.flight_number,
        "origin": segment.origin,
        "destination": segment.destination,
        "departure": segment.departure.isoformat(),
        "arrival": segment.arrival.isoformat(),
        "terminal_origin": segment.terminal_origin,
        "terminal_destination": segment.terminal_destination,
        "airline": segment.airline,
        "aircraft": segment.aircraft,
        "seat": segment.seat,
        "cabin": segment.cabin,
    }


def segment_from_dict(raw: dict[str, str]) -> Segment:
    return Segment(
        raw["id"],
        raw["flight_number"],
        raw["origin"],
        raw["destination"],
        datetime.fromisoformat(raw["departure"]),
        datetime.fromisoformat(raw["arrival"]),
        raw.get("terminal_origin", ""),
        raw.get("terminal_destination", ""),
        raw.get("airline", ""),
        raw.get("aircraft", ""),
        raw.get("seat", ""),
        raw.get("cabin", "Economy"),
    )
