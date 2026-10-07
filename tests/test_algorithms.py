from __future__ import annotations

import random
from datetime import date, datetime, timedelta, timezone

import pytest

from agent.cases import InvalidTransition, transition
from agent.detector import Segment, missed_segment_id
from agent.ranker import DEMO_INVENTORY, Itinerary, block_reason, legal_itineraries, rank_itineraries
from agent.trip import seed_segments


def test_rank_order_matches_the_hand_checked_fixture() -> None:
    rows = [
        Itinerary("a", "A", 10, 5000, 1, 90, "economy", date(2026, 10, 8), "a"),
        Itinerary("b", "B", 10, 4000, 0, 90, "economy", date(2026, 10, 8), "b"),
        Itinerary("c", "C", 5, 9000, 1, 20, "economy", date(2026, 10, 8), "c"),
        Itinerary("d", "D", 400, 1000, 0, 80, "economy", date(2026, 10, 9), "d"),
        Itinerary("e", "E", 30, 1000, 0, 50, "business", date(2026, 10, 8), "e"),
        Itinerary("f", "F", 10, 4000, 1, 45, "economy", date(2026, 10, 8), "f"),
    ]
    assert [row.id for row in rank_itineraries(rows)] == ["b", "f", "a"]


def test_rank_scales_and_matches_a_slow_reference() -> None:
    random.seed(7)
    rows = [
        Itinerary(
            f"n{index}",
            f"F{index}",
            random.randint(0, 500),
            random.randint(1000, 90_000),
            random.randint(0, 1),
            random.randint(10, 120),
            random.choice(["economy", "business"]),
            date(2026, 10, 8),
            "generated",
        )
        for index in range(2000)
    ]
    ranked = rank_itineraries(rows)
    reference = sorted(
        [row for row in rows if row.cabin == "economy" and row.connection_minutes >= 40 and row.delay_minutes <= 360],
        key=lambda row: (row.delay_minutes, row.fare_delta_cents, row.airline_penalty, row.id),
    )
    assert [row.id for row in ranked] == [row.id for row in reference]


def test_the_cheap_toronto_ticket_and_the_tight_heathrow_change_are_rejected() -> None:
    legal = legal_itineraries(DEMO_INVENTORY)
    assert legal[0].id == "itin-220"
    canada = next(row for row in DEMO_INVENTORY if row.id == "itin-yyz")
    heathrow = next(row for row in DEMO_INVENTORY if row.id == "itin-180")
    assert "Canada" in (block_reason(canada) or "")
    assert "90" in (block_reason(heathrow) or "")
    assert [row.id for row in rank_itineraries(DEMO_INVENTORY)][0] == "itin-yyz"


def test_seed_connection_is_legal_until_the_inbound_is_delayed() -> None:
    assert missed_segment_id(seed_segments()) is None
    delayed = []
    for segment in seed_segments():
        if segment.id == "ua410":
            delayed.append(
                Segment(
                    segment.id,
                    segment.flight_number,
                    segment.origin,
                    segment.destination,
                    segment.departure,
                    segment.arrival + timedelta(minutes=80),
                )
            )
        else:
            delayed.append(segment)
    assert missed_segment_id(delayed) == "ua882"


def test_missed_connection_uses_terminal_mct_not_flat_40() -> None:
    base = datetime(2026, 10, 8, 8, 0, tzinfo=timezone.utc)
    inbound = Segment(
        "in", "AI111", "DEL", "LHR", base, base + timedelta(hours=7, minutes=30),
        terminal_origin="T3", terminal_destination="T2",
    )
    # 50 min slack: flat 40 ke hisaab se legal, par T2->T5 ko 90 chahiye.
    outbound = Segment(
        "out", "BA173", "LHR", "JFK", base + timedelta(hours=8, minutes=20), base + timedelta(hours=16),
        terminal_origin="T5", terminal_destination="T8",
    )
    assert missed_segment_id([inbound, outbound]) == "out"
    # Same terminal T5->T5 ko 60 chahiye: 50 miss, 65 legal.
    tight = Segment(
        "tight", "BA115", "LHR", "JFK", base + timedelta(hours=8, minutes=20), base + timedelta(hours=16),
        terminal_origin="T2", terminal_destination="T8",
    )
    assert missed_segment_id([inbound, tight]) == "tight"
    relaxed = Segment(
        "relaxed", "BA117", "LHR", "JFK", base + timedelta(hours=8, minutes=35), base + timedelta(hours=16),
        terminal_origin="T2", terminal_destination="T8",
    )
    assert missed_segment_id([inbound, relaxed]) is None


def test_illegal_transition_writes_nothing() -> None:
    with pytest.raises(InvalidTransition):
        transition("Watching", "adapter_ok")


def test_every_legal_edge_moves() -> None:
    assert transition("Watching", "disruption") == "Disrupted"
    assert transition("Confirmed", "notified") == "Confirmed"
    assert transition("Blocked", "reset") == "Watching"


def test_index_lookup_finds_the_missed_flight() -> None:
    base = datetime(2026, 10, 8, 8, 0, tzinfo=timezone.utc)
    segments = [
        Segment("c", "C", "LHR", "JFK", base + timedelta(hours=6), base + timedelta(hours=10)),
        Segment("a", "A", "DEL", "LHR", base, base + timedelta(hours=4)),
        Segment("b", "B", "XXX", "YYY", base + timedelta(hours=5), base + timedelta(hours=5, minutes=30)),
    ]
    assert missed_segment_id(segments) == "c"
