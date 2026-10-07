# Concierge — system design (standalone, no governance calls)

## What it is
Three card members (Ananya DEL-LHR-JFK, Rohan BOM-FRA-ORD, Priya DEL-LHR-SFO),
one switcher on the page, per-trip snapshots/cases/caps/notifications in
Postgres. No rebook button anywhere. A cancellation or a short connection
fires the agent, which ranks that trip's replacements and books on its own
desk, then notifies on WhatsApp-style thread. Refresh-safe: state lives in
Postgres, not in memory. Unknown trip ids 404.

## Flow
```
Presenter              FastAPI (8002)              Postgres (5434)
   |  POST /v1/sim/disruptions  |                         |
   |--------------------------->|  snapshot + case row    |
   |                            |------------------------>|
   |                            |  loop: rank -> desk x3  |
   |                            |  -> snapshot reissue    |
   |  poll /v1/trips + /events  |  -> notifications row   |
   |<---------------------------|                         |
   |  EventSource /stream (SSE) |                         |
   |<---------------------------|                         |
```

## Components (all inside concierge/)
- `agent/detector.py` — cancellation + missed-connection (inbound delay leaves
  less than that pair's MCT; `mct_minutes()` in ranker.py is the single table,
  flat 40 is only the floor).
- `agent/benefit.py` — pure split truth (half MR / half card) + lounge status
  sentences; quote API and tests import this, no DB.
- `agent/ranker.py` — visa gate (Canada entry, Dubai transit), terminal-aware
  minimums (LHR T2->T5 90, same-T5 60, FRA 45, YYZ 75), cabin/delay gates,
  sorted by delay then fare. `block_reason()` returns the exact sentence the
  UI shows — no generic "not available".
- `agent/loop.py` — state machine (Watching -> Disrupted -> Planning ->
  AwaitingAuth -> Executing -> Confirmed/Blocked). Tries top-3 fares against
  the benefit cap, keeps hotel if arrival date moves, then notifies.
- `agent/desk.py` — the booking truth: attempts/committed counters,
  idempotency cache, cap check. No airline credentials leave this process.
- `agent/store.py` + `schema.sql` — per-trip snapshots, cases, events,
  notifications. Reset reseeds all trips.
- `agent/trip.py` — TRIPS registry (passenger/hotel/seed/inventory per trip),
  `route_summary()` for the switcher.
- `web/` — trip switcher, departure board, track, fare cards with MR+card
  split, lounge line, hotel +N extension line, time scrubber (replay lens
  only), Live badge.

## API table
| Method | Path | Use |
|---|---|---|
| GET | /v1/health | liveness |
| GET | /v1/ready | all trip snapshots readable (trips list, else 503) |
| GET | /v1/trips | id + member + route for the switcher |
| GET | /v1/trips/{id} | snapshot + case + notifications |
| GET | /v1/trips/{id}/events | case trace |
| GET | /v1/trips/{id}/stream | SSE live feed (EventSource) |
| GET | /v1/trips/{id}/ics | calendar download of live itinerary |
| GET | /v1/trips/{id}/board | top-3 legal + up to 6 blocked with reasons |
| POST | /v1/fare-quote | {trip_id, fare} -> half MR / half card + per-trip within_cap |
| GET | /v1/cases?trip_id= | disruption inbox, newest first |
| POST | /v1/desk/fare-limit | {trip_id, cap} — caps are per trip |
| GET | /v1/desk | per-trip caps + attempts/committed counters |
| POST | /v1/sim/disruptions | {trip_id, cancellation, missed_connection} — 404 unknown trip |
| POST | /v1/sim/reset | reseed all trips + clear caps |

## Failure modes (honest)
- Cap too low -> Blocked, nothing booked, WhatsApp stays quiet. Correct.
- All 3 fares over cap -> `no_candidate`, state Blocked with reason.
- Unknown trip id -> 404, nothing fires.
- DB down -> /v1/ready 503s; compose healthcheck gates the API on postgres.

## Scale notes
- Stateless API + Postgres. Two replicas can serve reads; writes go through
  one case row per disruption (idempotency_key per rebook).
- Poll 400ms is fine for a demo; SSE already streams events for ops.
- Load (`python bench.py`, local Docker): board p95 ~23ms at 20 req,
  ~65ms at 50-burst. Read-path only.

## 3-minute college demo script
1. Open 5174 (Ananya). Board On time, connection 95 min. Scrubber to 07:55 IST,
   press `1. Cancel AI111`: Toronto rejected (visa), T2->T5 rejected (needs 90,
   has 80), BA143/BA115 booked. Board Reissued, WhatsApp Hinglish.
2. Switch to Rohan: `1. Cancel LH756` — Frankfurt 30-min rejected (needs 45),
   Dubai rejected (transit), LH756/LH402 booked, Rs 18,000.
3. Switch to Priya: `1. Cancel AI111` — Dubai + tight-Heathrow rejected,
   next-day Paris booked, hotel +1 night extended, WhatsApp says so.
4. `2. Benefit cap Rs 10,000` on any trip -> nothing booked. Punch line:
   "rule toota, paisa ruka, agent muda — chat box nahi."
