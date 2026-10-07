from __future__ import annotations

TRANSITIONS: dict[tuple[str, str], str] = {
    ("Watching", "disruption"): "Disrupted",
    ("Disrupted", "plan"): "Planning",
    ("Planning", "candidate_chosen"): "AwaitingAuth",
    ("Planning", "no_candidate"): "Blocked",
    ("AwaitingAuth", "cap_denied"): "Planning",
    ("AwaitingAuth", "authorize_deny"): "Blocked",
    ("AwaitingAuth", "authorize_allow"): "Executing",
    ("Executing", "adapter_ok"): "Confirmed",
    ("Executing", "adapter_error"): "Failed",
    ("Confirmed", "hotel_chosen"): "AwaitingAuth",
    ("AwaitingAuth", "hotel_deny"): "Confirmed",
    ("Confirmed", "notified"): "Confirmed",
    ("Confirmed", "notify_denied"): "Confirmed",
    ("Blocked", "reset"): "Watching",
    ("Confirmed", "reset"): "Watching",
    ("Failed", "reset"): "Watching",
    ("Watching", "reset"): "Watching",
}


class InvalidTransition(Exception):
    pass


def transition(state: str, event: str) -> str:
    key = (state, event)
    if key not in TRANSITIONS:
        raise InvalidTransition(f"{state} + {event}")
    return TRANSITIONS[key]


CAP_REASONS = {"AGENT_CAP", "TEAM_CAP", "FLEET_CAP"}

REASON_TEXT = {
    "AGENT_CAP": "Rebook stopped because the fare is above the trip benefit limit.",
    "TEAM_CAP": "Rebook stopped because it would exceed the travel benefits team spend cap.",
    "FLEET_CAP": "Rebook stopped because it would exceed the fleet spend cap.",
    "EMERGENCY_STOP": "Rebook stopped because an operator halted all agents.",
    "STALE_GENERATION": "Rebook stopped because an operator halted all agents.",
    "REVOKED": "Rebook stopped because this agent was revoked.",
    "ACTION_NOT_ALLOWED": "Rebook stopped because this agent is not allowed to take that action.",
    "POLICY_UNAVAILABLE": "Rebook stopped because the policy engine was unavailable.",
    "CONTROL_PLANE_UNAVAILABLE": "Rebook stopped because the control plane was unavailable.",
    "ADAPTER_FAILED": "Rebook failed because the airline did not confirm the booking.",
    "AGENT_NOT_FOUND": "Rebook stopped because the agent is not registered.",
    "OK": "Rebook confirmed.",
}


def reason_text(reason_code: str) -> str:
    return REASON_TEXT.get(reason_code, f"Rebook stopped ({reason_code}).")
