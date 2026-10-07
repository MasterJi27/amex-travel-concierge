from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from agent.ranker import mct_minutes


@dataclass(frozen=True)
class Segment:
    id: str
    flight_number: str
    origin: str
    destination: str
    departure: datetime
    arrival: datetime
    terminal_origin: str = ""
    terminal_destination: str = ""
    airline: str = ""
    aircraft: str = ""
    seat: str = ""
    cabin: str = "Economy"


def index_segments(segments: list[Segment]) -> dict[str, int]:
    ordered = sorted(segments, key=lambda segment: segment.departure)
    return {segment.id: position for position, segment in enumerate(ordered)}


def missed_segment_id(segments: list[Segment], minimum_minutes: int = 40) -> str | None:
    ordered = sorted(segments, key=lambda segment: (segment.departure, segment.id))
    positions = index_segments(ordered)
    for segment in ordered:
        position = positions[segment.id]
        if position >= len(ordered) - 1:
            continue
        following = ordered[position + 1]
        slack_minutes = (following.departure - segment.arrival).total_seconds() / 60
        needed = max(
            mct_minutes(segment.destination, segment.terminal_destination, following.terminal_origin),
            minimum_minutes,
        )
        if slack_minutes < needed:
            return following.id
    return None


def delay_arrival(segment: Segment, minutes: int) -> Segment:
    return Segment(
        id=segment.id,
        flight_number=segment.flight_number,
        origin=segment.origin,
        destination=segment.destination,
        departure=segment.departure,
        arrival=segment.arrival + timedelta(minutes=minutes),
        terminal_origin=segment.terminal_origin,
        terminal_destination=segment.terminal_destination,
        airline=segment.airline,
        aircraft=segment.aircraft,
        seat=segment.seat,
        cabin=segment.cabin,
    )
