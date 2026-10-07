from __future__ import annotations

import pytest

from agent.benefit import lounge_line, split_fare


def test_ba_fare_splits_equal_mr_and_card() -> None:
    quote = split_fare(22_000)
    assert quote["mr_cover_cents"] == 11_000
    assert quote["card_pay_cents"] == 11_000
    assert quote["mr_points"] == round(11_000 / 0.35)


def test_zero_fare_and_negative_fare() -> None:
    assert split_fare(0) == {
        "fare_delta_cents": 0,
        "mr_cover_cents": 0,
        "mr_points": 0,
        "card_pay_cents": 0,
    }
    with pytest.raises(ValueError):
        split_fare(-100)


def test_lounge_void_then_reissued() -> None:
    assert "booked on AI111" in lounge_line(False, False)
    assert "void" in lounge_line(True, False)
    line = lounge_line(True, True, "BA143")
    assert "void on AI111" in line and "BA143" in line
