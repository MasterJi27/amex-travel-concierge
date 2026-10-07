# Autonomous Travel-Disruption Concierge

**Flight cancel ho ya connection miss ho — agent khud rebook karta hai. Member ko sirf WhatsApp aata hai. Page pe rebook button nahi hai.**

## Purpose — ye kya solve karta hai?

Flight cancellations and missed connections are stressful, and today they mean
manual rebooking: call the airline, wait on hold, compare options while the
clock runs. This project is an **agentic AI concierge** for premium travel
cards that detects a disruption the moment it occurs and **autonomously
rebooks flights, extends the hotel, and notifies the member** — no manual
action, no chat box. The model (when plugged in) doesn't chat; it calls three
tools: `search`, `rebook`, `notify`. Booking is always done by code.

What the judge remembers in 90 seconds:

1. **Rule toota** — sasti Toronto ticket reject (visa galat), tight Heathrow
   reject (walk galat), business cabin reject (benefit economy hai).
2. **Paisa ruka** — cap se upar ka fare book hi nahi hota, WhatsApp quiet rehta hai.
3. **Agent muda** — agla legal option book, board Reissued, hotel shift.

## Demo (3 trips, switcher on top)

```bash
cd deploy
docker compose up --build
```

Card-member page: **http://localhost:5174** · API: http://localhost:8002

1. **Ananya** (DEL T3 → LHR → JFK): `1. Cancel AI111` → Toronto visa reject,
   T2→T5 80<90 reject, **BA143/BA115 ₹22,000** booked. Board Reissued.
2. **Rohan** (BOM T2 → FRA T1 → ORD T5): `1. Cancel LH756` → Frankfurt 30-min
   reject (45 chahiye), Dubai transit reject, **LH756/LH402 ₹18,000** booked.
3. **Priya** (DEL T3 → LHR → SFO): `1. Cancel AI111` → Dubai + tight-Heathrow
   reject, same-day kuch legal nahi → **next-day Paris booked, hotel +1 night
   extended**, WhatsApp says so.
4. `2. Benefit cap ₹10,000` on any trip → kuch book nahi hota.
5. Inbound-delay slider chhodo → threshold ke neeche "abhi legal 65/45",
   upar agent fire. Alag airport, alag rule — wahi dikhta hai.

## How it works

- **Detector** (`agent/detector.py`): cancellation + missed-connection. MCT per
  pair aata hai — ek shared `mct_minutes()` table (LHR T2→T5 90, same 60,
  FRA 45, YYZ 75), flat 40 sirf floor hai.
- **Ranker** (`agent/ranker.py`): visa gate (Canada entry, Dubai transit —
  US B1/B2 covers neither), cabin + 6h-delay gates. Sort: delay, then fare.
  `block_reason()` wahi sentence deta hai jo screen pe dikhta hai.
- **Loop** (`agent/loop.py`): Watching → Disrupted → Planning → AwaitingAuth →
  Executing → Confirmed/Blocked. Top-3 fares try karta hai, next-day pe hotel
  extend, phir Hinglish notify.
- **Desk** (`agent/desk.py`): booking truth — per-trip benefit caps,
  idempotency cache, counters. Koi dusri service call nahi hoti.
- **Benefit** (`agent/benefit.py`): half MR / half card split + lounge status,
  pure functions — API aur tests ek hi truth import karte hain.
- **Live**: SSE stream (pehli line <1s), `.ics` calendar download, disruption
  inbox, per-trip fare-quote. Full design: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

## API

| Method | Path | Use |
|---|---|---|
| GET | /v1/health · /v1/ready | liveness · snapshots readable (else 503) |
| GET | /v1/trips | id + member + route (switcher) |
| GET | /v1/trips/{id} · /events · /board · /stream · /ics | snapshot · trace · fares · SSE · calendar |
| POST | /v1/fare-quote | {trip_id, fare} → MR/card split + within_cap |
| GET | /v1/cases?trip_id= | disruption inbox |
| POST | /v1/desk/fare-limit | {trip_id, cap} — caps are per trip |
| POST | /v1/sim/disruptions | {trip_id, cancellation, missed_connection} |
| POST | /v1/sim/reset | reseed all trips |

## File structure

```
travel-concierge/
├── agent/            # detector, ranker, loop, desk, benefit, trip registry, store, server
│   ├── trip.py       # TRIPS registry: passengers, hotels, seeds, inventories
│   └── schema.sql    # snapshots, cases, events, notifications
├── web/              # card page (React + Vite): board, fares, trace, WhatsApp
├── tests/            # ranker/detector/benefit/loop/boundary (no Docker needed)
├── deploy/           # docker-compose.yml + Dockerfile (pg 5434, api 8002, web 5174)
├── docs/             # ARCHITECTURE.md — full system design
├── bench.py          # read-path load (stdlib only)
└── requirements.txt  # fastapi, uvicorn, psycopg, pydantic, pytest
```

## Tests & load

```bash
python -m pytest            # unit tests, Docker nahi chahiye
python bench.py 50 50       # read-path: board p95 ~65ms burst, ~23ms @20 req
```

## Tech

Python (FastAPI) · Postgres 16 · React + Vite · SSE · Docker Compose.
