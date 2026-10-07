from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone


@dataclass(frozen=True)
class Itinerary:
    id: str
    flight_numbers: str
    delay_minutes: int
    fare_delta_cents: int
    airline_penalty: int
    connection_minutes: int
    cabin: str
    arrival_date: date
    summary: str
    origin: str = "DEL"
    via: str = "LHR"
    destination: str = "JFK"
    airline: str = ""
    aircraft: str = ""
    baggage: str = "2 × 23 kg"
    arrive_terminal: str = "T5"
    leave_terminal: str = "T5"
    entry: str = "airside"


ORIGINAL_CABIN = "economy"
ORIGINAL_ARRIVAL = date(2026, 10, 8)
MAX_DELAY_MINUTES = 360
MIN_CONNECTION_MINUTES = 40
HOTEL_NIGHT_CENTS = 24_000


def rank_itineraries(
    rows: list[Itinerary],
    cabin: str = ORIGINAL_CABIN,
    max_delay: int = MAX_DELAY_MINUTES,
    min_connection: int = MIN_CONNECTION_MINUTES,
) -> list[Itinerary]:
    feasible = [
        row
        for row in rows
        if row.cabin == cabin and row.connection_minutes >= min_connection and row.delay_minutes <= max_delay
    ]
    return sorted(feasible, key=lambda row: (row.delay_minutes, row.fare_delta_cents, row.airline_penalty, row.id))


DEMO_INVENTORY: list[Itinerary] = [
    Itinerary(
        "itin-yyz",
        "AC850/AC702",
        25,
        12_000,
        1,
        95,
        "economy",
        date(2026, 10, 8),
        "Air Canada via Toronto. Cheapest, and the soonest.",
        via="YYZ",
        airline="Air Canada",
        aircraft="787-9 / A220",
        arrive_terminal="1",
        leave_terminal="1",
        entry="canada",
    ),
    Itinerary(
        "itin-180",
        "AI111/BA173",
        40,
        18_000,
        0,
        80,
        "economy",
        date(2026, 10, 8),
        "Air India to Heathrow, British Airways to JFK, 40 min later",
        airline="Air India / British Airways",
        aircraft="787-8 / A350",
        arrive_terminal="T2",
        leave_terminal="T5",
    ),
    Itinerary(
        "itin-220",
        "BA143/BA115",
        70,
        22_000,
        1,
        75,
        "economy",
        date(2026, 10, 8),
        "British Airways all the way via Heathrow, 70 min later",
        airline="British Airways",
        aircraft="777-300ER / A350",
        arrive_terminal="T5",
        leave_terminal="T5",
    ),
    Itinerary(
        "itin-260",
        "LH760/LH400",
        80,
        26_000,
        1,
        90,
        "economy",
        date(2026, 10, 8),
        "Lufthansa via Frankfurt, 80 min later",
        via="FRA",
        airline="Lufthansa",
        aircraft="A350 / A340",
        arrive_terminal="T1",
        leave_terminal="T1",
    ),
    Itinerary(
        "itin-300",
        "EK510/EK202",
        150,
        31_000,
        1,
        70,
        "economy",
        date(2026, 10, 8),
        "Emirates via Dubai",
        via="DXB",
        airline="Emirates",
        aircraft="A380",
        entry="dxb-transit",
    ),
    Itinerary("itin-short", "AI201/BA115", 20, 5_000, 0, 20, "economy", date(2026, 10, 8), "Too short a connection at Heathrow"),
    Itinerary("itin-late", "AI105/BA117", 400, 4_000, 0, 80, "economy", date(2026, 10, 9), "Lands after the same-day window"),
    Itinerary("itin-cabin", "AI101/BA175", 15, 8_000, 0, 90, "business", date(2026, 10, 8), "Business cabin"),
    Itinerary("itin-nextday", "AF225/AF010", 320, 90_000, 1, 100, "economy", date(2026, 10, 9), "Next-day arrival"),
    Itinerary("itin-340", "QR570/QR572", 200, 34_000, 1, 85, "economy", date(2026, 10, 8), "Qatar via Doha", via="DOH", airline="Qatar Airways"),
    Itinerary("itin-280", "VS300/VS004", 130, 28_000, 1, 60, "economy", date(2026, 10, 8), "Virgin Atlantic via London", airline="Virgin Atlantic"),
    Itinerary("itin-240", "DL250/DL402", 95, 24_000, 1, 55, "economy", date(2026, 10, 8), "Delta via London", airline="Delta"),
    Itinerary("itin-360", "SQ422/SQ026", 250, 36_000, 1, 95, "economy", date(2026, 10, 8), "Singapore Airlines via Singapore", via="SIN", airline="Singapore Airlines"),
]


INVENTORY_2402: list[Itinerary] = [
    Itinerary(
        "r2-lh",
        "LH756/LH402",
        45,
        18_000,
        0,
        55,
        "economy",
        date(2026, 10, 8),
        "Lufthansa via Frankfurt, 45 min later",
        origin="BOM",
        via="FRA",
        destination="ORD",
        airline="Lufthansa",
        aircraft="A350 / A340",
        arrive_terminal="T1",
        leave_terminal="T1",
    ),
    Itinerary(
        "r2-short",
        "LH756/LH410",
        20,
        9_000,
        0,
        30,
        "economy",
        date(2026, 10, 8),
        "Too short a connection at Frankfurt",
        origin="BOM",
        via="FRA",
        destination="ORD",
        airline="Lufthansa",
        aircraft="A350 / A340",
        arrive_terminal="T1",
        leave_terminal="T1",
    ),
    Itinerary(
        "r2-ek",
        "EK504/EK203",
        150,
        31_000,
        1,
        70,
        "economy",
        date(2026, 10, 8),
        "Emirates via Dubai",
        origin="BOM",
        via="DXB",
        destination="ORD",
        airline="Emirates",
        aircraft="A380",
        entry="dxb-transit",
    ),
    Itinerary(
        "r2-qr",
        "QR556/QR725",
        200,
        34_000,
        1,
        85,
        "economy",
        date(2026, 10, 8),
        "Qatar via Doha",
        origin="BOM",
        via="DOH",
        destination="ORD",
        airline="Qatar Airways",
        aircraft="777 / A350",
    ),
]

INVENTORY_2403: list[Itinerary] = [
    Itinerary(
        "s3-ek",
        "EK510/EK202",
        150,
        31_000,
        1,
        70,
        "economy",
        date(2026, 10, 8),
        "Emirates via Dubai",
        origin="DEL",
        via="DXB",
        destination="SFO",
        airline="Emirates",
        aircraft="A380",
        entry="dxb-transit",
    ),
    Itinerary(
        "s3-tight",
        "AI111/BA285",
        80,
        19_000,
        0,
        80,
        "economy",
        date(2026, 10, 8),
        "Air India to Heathrow, BA to San Francisco, T2 to T5 walk too short",
        origin="DEL",
        via="LHR",
        destination="SFO",
        airline="Air India / British Airways",
        aircraft="787-8 / A380",
        arrive_terminal="T2",
        leave_terminal="T5",
    ),
    Itinerary(
        "s3-af",
        "AI201/AF011",
        300,
        15_000,
        1,
        70,
        "economy",
        date(2026, 10, 9),
        "Air France via Paris, next-day arrival, hotel extends",
        origin="DEL",
        via="CDG",
        destination="SFO",
        airline="Air India / Air France",
        aircraft="787-8 / 777",
        arrive_terminal="2E",
        leave_terminal="2E",
    ),
]


def hotel_nights(arrival: date, checkin: date = ORIGINAL_ARRIVAL) -> int:
    return max(0, (arrival - checkin).days)


def mct_minutes(via: str, arrive_terminal: str, leave_terminal: str) -> int:
    """Minimum connection time for one join. Single source of truth: the
    ranker and the missed-connection detector both use this."""
    if via == "LHR" and arrive_terminal != leave_terminal:
        return 90
    if via == "LHR":
        return 60
    if via == "FRA":
        return 45
    if via == "YYZ":
        return 75
    return MIN_CONNECTION_MINUTES


def connection_rule(row: Itinerary) -> tuple[int, str]:
    needed = mct_minutes(row.via, row.arrive_terminal, row.leave_terminal)
    if row.via == "LHR" and row.arrive_terminal != row.leave_terminal:
        return needed, f"Heathrow {row.arrive_terminal} to {row.leave_terminal}"
    if row.via == "LHR":
        return needed, f"Heathrow {row.arrive_terminal} same terminal"
    if row.via == "FRA":
        return needed, "Frankfurt international"
    if row.via == "YYZ":
        return needed, "Toronto after immigration"
    return needed, row.via


def block_reason(row: Itinerary) -> str | None:
    if row.cabin != ORIGINAL_CABIN:
        return "Business cabin. This benefit is economy."
    if row.delay_minutes > MAX_DELAY_MINUTES:
        return "Lands more than 6 hours late."
    if row.entry == "canada":
        return "Toronto makes the passenger enter Canada. A US B1/B2 is not a Canadian visa or eTA."
    if row.via == "DXB" or row.entry == "dxb-transit":
        return "Dubai transit needs a UAE transit visa. Indian passport + US B1/B2 does not cover it."
    needed, place = connection_rule(row)
    if row.connection_minutes < needed:
        return f"{place} needs {needed} minutes. This connection is {row.connection_minutes}."
    return None


def skip_reason(row: Itinerary) -> str | None:
    return block_reason(row)


def legal_itineraries(rows: list[Itinerary]) -> list[Itinerary]:
    legal = [row for row in rows if block_reason(row) is None]
    return sorted(legal, key=lambda row: (row.delay_minutes, row.fare_delta_cents, row.airline_penalty, row.id))


def as_public(row: Itinerary) -> dict[str, object]:
    return {
        "id": row.id,
        "flight_numbers": row.flight_numbers,
        "delay_minutes": row.delay_minutes,
        "fare_delta_cents": row.fare_delta_cents,
        "connection_minutes": row.connection_minutes,
        "summary": row.summary,
        "origin": row.origin,
        "via": row.via,
        "destination": row.destination,
        "airline": row.airline,
        "aircraft": row.aircraft,
        "baggage": row.baggage,
        "arrive_terminal": row.arrive_terminal,
        "leave_terminal": row.leave_terminal,
        "entry": row.entry,
    }


def replacement_segments(row: Itinerary) -> list[dict[str, str]]:
    first, second = row.flight_numbers.split("/")
    carriers = [part.strip() for part in row.airline.split("/")] if row.airline else ["", ""]
    if len(carriers) == 1:
        carriers = [carriers[0], carriers[0]]
    planes = [part.strip() for part in row.aircraft.split("/")] if row.aircraft else ["", ""]
    if len(planes) == 1:
        planes = [planes[0], planes[0]]
    depart = datetime(2026, 10, 8, 9, 0, tzinfo=timezone.utc)
    arrive_via = depart + timedelta(hours=9, minutes=30)
    leave_via = arrive_via + timedelta(minutes=row.connection_minutes)
    arrive_dest = leave_via + timedelta(hours=8)
    origin_terminal = "T3" if row.origin == "DEL" else ""
    dest_terminal = "T8" if row.destination == "JFK" else ""
    return [
        {
            "id": f"{row.id}-1",
            "flight_number": first,
            "origin": row.origin,
            "destination": row.via,
            "departure": depart.isoformat(),
            "arrival": arrive_via.isoformat(),
            "terminal_origin": origin_terminal,
            "terminal_destination": row.arrive_terminal,
            "airline": carriers[0],
            "aircraft": planes[0],
            "seat": "14C",
            "cabin": "Economy",
        },
        {
            "id": f"{row.id}-2",
            "flight_number": second,
            "origin": row.via,
            "destination": row.destination,
            "departure": leave_via.isoformat(),
            "arrival": arrive_dest.isoformat(),
            "terminal_origin": row.leave_terminal,
            "terminal_destination": dest_terminal,
            "airline": carriers[1],
            "aircraft": planes[1],
            "seat": "22A",
            "cabin": "Economy",
        },
    ]
