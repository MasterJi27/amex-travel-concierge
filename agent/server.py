from __future__ import annotations

import asyncio
import json
import os
import time
import uuid
from datetime import datetime

import psycopg
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse, StreamingResponse
from pydantic import BaseModel

from agent.benefit import split_fare
from agent.desk import BookingDesk
from agent.detector import delay_arrival, missed_segment_id
from agent.loop import resolve_disruption
from agent.ranker import as_public, block_reason, legal_itineraries, mct_minutes, replacement_segments
from agent.store import ConciergeDb, segments_from_body
from agent.trip import SEED_VERSION, TRIP_ID, TRIPS, TRIP_INVENTORIES, route_summary, segment_to_dict

app = FastAPI(title="Travel Concierge")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _require_trip(trip_id: str) -> dict[str, object]:
    try:
        return TRIPS[trip_id]
    except KeyError:
        raise HTTPException(status_code=404, detail=f"unknown trip {trip_id}") from None


def _database_url() -> str:
    if "DATABASE_URL" in os.environ:
        return os.environ["DATABASE_URL"]
    try:
        user = os.environ["POSTGRES_USER"]
        secret = os.environ["POSTGRES_PASSWORD"]
        dbname = os.environ["POSTGRES_DB"]
    except KeyError as exc:
        raise RuntimeError(
            "Set DATABASE_URL or copy deploy/.env.example to deploy/.env "
            "(compose always sets DATABASE_URL, so this only affects bare-metal runs)"
        ) from exc
    return f"postgresql://{user}:{secret}@localhost:5434/{dbname}"


db = ConciergeDb(_database_url())
desk = BookingDesk()


class DisruptionIn(BaseModel):
    trip_id: str = TRIP_ID
    type: str
    segment_id: str = ""
    delay_minutes: int = 80


class FareLimitIn(BaseModel):
    trip_id: str = TRIP_ID
    max_fare_cents: int


class FareQuoteIn(BaseModel):
    trip_id: str = TRIP_ID
    fare_delta_cents: int


@app.on_event("startup")
def startup() -> None:
    database_url = os.environ["DATABASE_URL"] if "DATABASE_URL" in os.environ else db.url
    for _ in range(60):
        try:
            with psycopg.connect(database_url) as conn:
                conn.execute("SELECT 1")
            db.apply_schema()
            if db.snapshot(TRIP_ID).get("version") != SEED_VERSION:
                db.reset()
            return
        except Exception:
            time.sleep(1)
    raise RuntimeError("postgres did not become ready")


@app.get("/v1/health")
def health() -> dict[str, bool]:
    return {"ok": True}


@app.get("/v1/ready")
def ready() -> dict[str, object]:
    """Readiness: every seeded trip snapshot must be readable."""
    try:
        ids = sorted(TRIPS)
        for trip_id in ids:
            db.snapshot(trip_id)
        return {"ready": True, "trips": ids}
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"postgres not readable: {exc}")


@app.get("/v1/trips")
def trip_list() -> dict[str, object]:
    trips = []
    for trip_id in sorted(TRIPS):
        passenger = TRIPS[trip_id]["passenger"]
        trips.append(
            {
                "id": trip_id,
                "name": passenger["name"],
                "card": passenger["card"],
                "route": route_summary(trip_id),
            }
        )
    return {"trips": trips}


@app.get("/v1/trips/{trip_id}")
def trip(trip_id: str) -> dict[str, object]:
    _require_trip(trip_id)
    body = db.snapshot(trip_id)
    latest = db.latest_case(trip_id)
    return {
        "trip": body,
        "case": None
        if latest is None
        else {"id": latest["id"], "state": latest["state"], "created_at": latest["created_at"].isoformat()},
        "notifications": db.notifications(trip_id),
    }


@app.get("/v1/trips/{trip_id}/events")
def events(trip_id: str) -> dict[str, object]:
    _require_trip(trip_id)
    latest = db.latest_case(trip_id)
    if latest is None:
        return {"case": None, "events": []}
    return {
        "case": {"id": latest["id"], "state": latest["state"]},
        "events": db.events(str(latest["id"])),
    }


@app.get("/v1/cases")
def cases(trip_id: str = "", limit: int = 10) -> dict[str, object]:
    """Disruption inbox, newest first. Filter with ?trip_id=trip-2402."""
    if trip_id:
        _require_trip(trip_id)
        return {"cases": db.recent_cases(limit, trip_id)}
    return {"cases": db.recent_cases(limit)}


@app.post("/v1/sim/reset")
def reset() -> dict[str, bool]:
    db.reset()
    desk.reset()
    return {"ok": True}


@app.post("/v1/desk/fare-limit")
def fare_limit(body: FareLimitIn) -> dict[str, int]:
    _require_trip(body.trip_id)
    try:
        cap = desk.set_cap(body.trip_id, body.max_fare_cents)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"max_fare_cents": cap}


@app.get("/v1/trips/{trip_id}/board")
def board(trip_id: str) -> dict[str, object]:
    _require_trip(trip_id)
    inventory = TRIP_INVENTORIES[trip_id]
    legal = legal_itineraries(inventory)
    blocked = []
    for row in inventory:
        reason = block_reason(row)
        if reason is not None:
            blocked.append({**as_public(row), "reason": reason})
    blocked.sort(key=lambda item: (int(item["delay_minutes"]), int(item["fare_delta_cents"])))
    return {
        "options": [as_public(row) for row in legal[:3]],
        "blocked": blocked[:6],
        "max_fare_cents": desk.cap_for(trip_id),
    }


@app.get("/v1/desk")
def desk_status() -> dict[str, object]:
    return {
        "caps": {trip_id: desk.cap_for(trip_id) for trip_id in sorted(TRIPS)},
        "flight_attempts": desk.flight_attempts,
        "flight_committed": desk.flight_committed,
    }


@app.post("/v1/fare-quote")
def fare_quote(body: FareQuoteIn) -> dict[str, object]:
    """Truth for the benefit split shown on cards. Half off MR, half on card."""
    _require_trip(body.trip_id)
    try:
        quote = split_fare(int(body.fare_delta_cents))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    cap = desk.cap_for(body.trip_id)
    return {
        **quote,
        "cap_cents": cap,
        "within_cap": int(body.fare_delta_cents) <= cap,
    }


def _ics_time(iso: str) -> str:
    moment = datetime.fromisoformat(iso)
    return moment.strftime("%Y%m%dT%H%M%SZ")


@app.get("/v1/trips/{trip_id}/ics")
def trip_ics(trip_id: str) -> PlainTextResponse:
    """Download the current itinerary as .ics so the trip is usable in a
    real calendar. Regenerates from the live snapshot, including reissues."""
    _require_trip(trip_id)
    body = db.snapshot(trip_id)
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//amex-concierge//trip-2401//EN",
    ]
    passenger = body.get("passenger", {})
    for segment in body.get("segments", []):
        lines += [
            "BEGIN:VEVENT",
            f"UID:{segment['id']}@{trip_id}",
            f"DTSTART:{_ics_time(segment['departure'])}",
            f"DTEND:{_ics_time(segment['arrival'])}",
            f"SUMMARY:{segment.get('flight_number', '')} {segment.get('origin', '')}->{segment.get('destination', '')}",
            f"DESCRIPTION:PNR {passenger.get('pnr', '')} Ticket {passenger.get('ticket', '')} Seat {segment.get('seat', '')}",
            f"LOCATION:{segment.get('origin', '')} {segment.get('terminal_origin', '')}",
            "END:VEVENT",
        ]
    lines.append("END:VCALENDAR")
    return PlainTextResponse(
        "\r\n".join(lines),
        media_type="text/calendar",
        headers={"Content-Disposition": f"attachment; filename={trip_id}.ics"},
    )


@app.get("/v1/trips/{trip_id}/stream")
async def trip_stream(trip_id: str) -> StreamingResponse:
    """Server-sent events for the latest case of one trip."""
    _require_trip(trip_id)

    async def generate():
        last_seen = -1
        idle = 0
        while True:
            latest = db.latest_case(trip_id)
            if latest is None:
                yield ": waiting for a case\n\n"
            else:
                for event in db.events(str(latest["id"])):
                    if int(event["id"]) > last_seen:
                        last_seen = int(event["id"])
                        yield f"data: {json.dumps(event, default=str)}\n\n"
                        idle = 0
            idle += 1
            if idle % 30 == 0:
                yield ": heartbeat\n\n"
            await asyncio.sleep(0.5)

    return StreamingResponse(generate(), media_type="text/event-stream")


@app.post("/v1/sim/disruptions")
async def disrupt(body: DisruptionIn) -> dict[str, object]:
    _require_trip(body.trip_id)
    if body.type not in {"cancellation", "missed_connection"}:
        raise HTTPException(status_code=400, detail="unknown disruption type")

    inventory = TRIP_INVENTORIES[body.trip_id]
    snapshot = db.snapshot(body.trip_id)
    segments = segments_from_body(snapshot)
    ordered = sorted(segments, key=lambda segment: segment.departure)
    target_id = body.segment_id or ordered[0].id
    if body.type == "missed_connection":
        updated = []
        for segment in segments:
            if segment.id == target_id:
                updated.append(delay_arrival(segment, body.delay_minutes))
            else:
                updated.append(segment)
        if missed_segment_id(updated) is None:
            ordered_pairs = sorted(updated, key=lambda segment: (segment.departure, segment.id))
            tightest = None
            for first, second in zip(ordered_pairs, ordered_pairs[1:]):
                slack = round((second.departure - first.arrival).total_seconds() / 60)
                needed = max(
                    mct_minutes(first.destination, first.terminal_destination, second.terminal_origin), 40
                )
                if tightest is None or slack - needed < tightest[0]:
                    tightest = (slack - needed, slack, needed)
            slack, needed = (tightest[1], tightest[2]) if tightest else (None, None)
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "connection is still legal",
                    "slack_minutes": slack,
                    "needed_minutes": needed,
                },
            )
        snapshot["segments"] = [segment_to_dict(segment) for segment in updated]
        db.save_snapshot(body.trip_id, snapshot)

    case_id = str(uuid.uuid4())
    db.insert_case(case_id, body.trip_id, "Watching")
    by_id = {row.id: row for row in inventory}
    passenger = snapshot.get("passenger", {})
    member_name = str(passenger.get("name", "Member")).split(" ")[0]
    inbound_flight = ordered[0].flight_number

    async def publish(event: dict[str, object]) -> None:
        detail = event["detail"]
        if event["event"] == "adapter_ok" and isinstance(detail, dict) and "itinerary_id" in detail:
            chosen = by_id[str(detail["itinerary_id"])]
            current = db.snapshot(body.trip_id)
            current["segments"] = replacement_segments(chosen)
            current["rebooked"] = chosen.id
            db.save_snapshot(body.trip_id, current)
        db.append_event(case_id, event, body.trip_id)
        await asyncio.sleep(0.7)

    log = await resolve_disruption(
        desk, inventory, case_id, body.type, sink=publish,
        trip_id=body.trip_id, member_name=member_name, inbound_flight=inbound_flight,
    )
    return {"case_id": case_id, "state": log.state, "events": log.events}


def main() -> None:
    uvicorn.run("agent.server:app", host="0.0.0.0", port=int(os.environ.get("PORT", "8002")))


if __name__ == "__main__":
    main()
