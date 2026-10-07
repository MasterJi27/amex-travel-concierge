from __future__ import annotations

MR_SHARE = 0.5
MR_RUPEES_PER_POINT = 0.35


def split_fare(fare_delta_cents: int) -> dict[str, int]:
    """Benefit split truth. Half the extra fare comes off Membership Rewards,
    half goes on the card. Pure function so the quote API and tests agree."""
    if fare_delta_cents < 0:
        raise ValueError("fare must be >= 0")
    mr_cover = int(fare_delta_cents * MR_SHARE)
    card_pay = fare_delta_cents - mr_cover
    return {
        "fare_delta_cents": fare_delta_cents,
        "mr_cover_cents": mr_cover,
        "mr_points": round(mr_cover / MR_RUPEES_PER_POINT) if mr_cover else 0,
        "card_pay_cents": card_pay,
    }


def lounge_line(disrupted: bool, rebooked: bool, new_flight: str = "") -> str:
    """Plaza Premium T3 status in one sentence. Cancel voids it, reissue moves it."""
    if rebooked:
        return f"Plaza Premium Lounge, Delhi T3 — void on AI111, reissued on {new_flight or 'new flight'}."
    if disrupted:
        return "Plaza Premium Lounge, Delhi T3 — void while AI111 is disrupted."
    return "Plaza Premium Lounge, Delhi T3 — booked on AI111."
