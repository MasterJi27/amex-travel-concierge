import { useEffect, useState } from "react";

const API = import.meta.env.VITE_API_URL || "http://localhost:8002";

const CITY = {
  DEL: "Delhi",
  BOM: "Mumbai",
  LHR: "London",
  JFK: "New York",
  ORD: "Chicago",
  SFO: "San Francisco",
  FRA: "Frankfurt",
  CDG: "Paris",
  DXB: "Dubai",
  DOH: "Doha",
  SIN: "Singapore",
  YYZ: "Toronto",
};

const ZONE = {
  DEL: ["Asia/Kolkata", "IST"],
  BOM: ["Asia/Kolkata", "IST"],
  LHR: ["Europe/London", "BST"],
  JFK: ["America/New_York", "EDT"],
  ORD: ["America/Chicago", "CDT"],
  SFO: ["America/Los_Angeles", "PDT"],
  FRA: ["Europe/Berlin", "CEST"],
  CDG: ["Europe/Paris", "CEST"],
  DXB: ["Asia/Dubai", "GST"],
  DOH: ["Asia/Qatar", "AST"],
  SIN: ["Asia/Singapore", "SGT"],
};

function localClock(iso, airport) {
  if (!iso) return "";
  const [zone, label] = ZONE[airport] || ["UTC", "UTC"];
  const time = new Date(iso).toLocaleTimeString("en-GB", {
    hour: "2-digit",
    minute: "2-digit",
    timeZone: zone,
  });
  return `${time} ${label}`;
}

function rupees(amount) {
  return `₹${Math.round(amount || 0).toLocaleString("en-IN")}`;
}

function benefitSplit(fare) {
  const mr = Math.floor((fare || 0) / 2);
  const card = (fare || 0) - mr;
  const pts = Math.round(mr / 0.35);
  return `${rupees(fare)} = ${rupees(mr)} MR (${pts.toLocaleString("en-IN")} pts) + ${rupees(card)} card`;
}

function slackMinutes(segments) {
  if (segments.length < 2) return null;
  const arrive = new Date(segments[0].arrival).getTime();
  const depart = new Date(segments[1].departure).getTime();
  return Math.round((depart - arrive) / 60000);
}

function sentence(event, segments) {
  const detail = event.detail || {};
  const first = segments[0];
  const second = segments[1];
  if (event.event === "disruption") {
    if (detail.kind === "missed_connection" && first && second) {
      return `${first.flight_number} is late into ${first.destination} ${first.terminal_destination}. The walk to ${second.flight_number} at ${second.terminal_origin} is no longer legal.`;
    }
    if (first) {
      return `${first.flight_number} ${first.origin} to ${first.destination} is cancelled. ${first.origin} ${first.terminal_origin} se nikalna tha. The concierge is looking for an economy seat.`;
    }
    return "Disruption detected. Looking for an economy seat.";
  }
  if (event.event === "plan") return "Same-day economy only. Sorted by delay, then extra fare, then staying on a partner airline.";
  if (event.event === "candidate_chosen") return `Asking the desk to reissue ${detail.summary}.`;
  if (event.event === "cap_denied" || event.event === "authorize_deny" || event.event === "no_candidate") {
    return detail.text || "That fare does not fit.";
  }
  if (event.event === "adapter_ok") return detail.text || "Booked.";
  if (event.event === "notified") return detail.message;
  if (detail.text) return detail.text;
  return event.event;
}

function optionStatus(id, events) {
  let status = "open";
  for (const event of events) {
    const detail = event.detail || {};
    if (event.event === "candidate_chosen" && detail.itinerary_id === id) status = "trying";
    if ((event.event === "cap_denied" || event.event === "authorize_deny") && detail.itinerary_id === id) {
      status = "denied";
    }
    if (event.event === "adapter_ok" && detail.itinerary_id === id) status = "booked";
  }
  return status;
}

const STATUS_LABEL = {
  open: "In the running",
  trying: "Asking the desk",
  denied: "Over the benefit",
  booked: "Booked",
};

function hotelExtensionNights(events) {
  let nights = 0;
  for (const event of events) {
    const detail = event.detail || {};
    if (typeof detail.nights === "number") nights = Math.max(nights, detail.nights);
  }
  return nights;
}

function addDays(dateStr, days) {
  const date = new Date(`${dateStr}T12:00:00`);
  date.setDate(date.getDate() + days);
  return date.toLocaleDateString("en-IN", { day: "numeric", month: "short" });
}

export default function App() {
  const [trips, setTrips] = useState([]);
  const [tripId, setTripId] = useState("trip-2401");
  const [trip, setTrip] = useState(null);
  const [events, setEvents] = useState([]);
  const [state, setState] = useState("Watching");
  const [cases, setCases] = useState([]);
  const [board, setBoard] = useState({ options: [], skipped: [] });
  const [hint, setHint] = useState("");
  const [busy, setBusy] = useState(false);
  const [scrub, setScrub] = useState(115);
  const [live, setLive] = useState(false);

  async function refresh(id) {
    const [tripRes, eventRes, boardRes, casesRes] = await Promise.all([
      fetch(`${API}/v1/trips/${id}`),
      fetch(`${API}/v1/trips/${id}/events`),
      fetch(`${API}/v1/trips/${id}/board`),
      fetch(`${API}/v1/cases?trip_id=${id}`).catch(() => null),
    ]);
    const tripBody = await tripRes.json();
    const eventBody = await eventRes.json();
    const boardBody = await boardRes.json();
    setTrip(tripBody);
    setEvents(eventBody.events || []);
    setState(eventBody.case?.state || "Watching");
    setBoard(boardBody);
    if (casesRes && casesRes.ok) {
      const casesBody = await casesRes.json();
      setCases(casesBody.cases || []);
    }
  }

  useEffect(() => {
    fetch(`${API}/v1/trips`)
      .then((res) => res.json())
      .then((body) => setTrips(body.trips || []))
      .catch((err) => setHint(String(err)));
  }, []);

  useEffect(() => {
    setLive(false);
    refresh(tripId).catch((err) => setHint(String(err)));
    const timer = setInterval(() => {
      refresh(tripId).catch(() => {});
    }, 400);
    let source = null;
    try {
      source = new EventSource(`${API}/v1/trips/${tripId}/stream`);
      source.onmessage = () => setLive(true);
      source.onerror = () => setLive(false);
    } catch {
      setLive(false);
    }
    return () => {
      clearInterval(timer);
      if (source) source.close();
    };
  }, [tripId]);

  async function resetAll() {
    await fetch(`${API}/v1/sim/reset`, { method: "POST" });
    setHint("");
    await refresh(tripId);
  }

  const [delayVal, setDelayVal] = useState(80);

  async function disrupt(type, delayMinutes = 80) {
    const response = await fetch(`${API}/v1/sim/disruptions`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ trip_id: tripId, type, segment_id: "", delay_minutes: delayMinutes }),
    });
    if (!response.ok) {
      const text = await response.text();
      try {
        const parsed = JSON.parse(text).detail || JSON.parse(text);
        if (parsed && typeof parsed === "object" && parsed.slack_minutes !== undefined) {
          setHint(`Abhi legal hai — connection ${parsed.slack_minutes}/${parsed.needed_minutes} min. Delay badhao.`);
        } else {
          setHint(text);
        }
      } catch {
        setHint(text);
      }
    }
    await refresh(tripId);
  }

  async function run(task) {
    setBusy(true);
    setHint("");
    try {
      await task();
    } catch (err) {
      setHint(String(err));
    } finally {
      setBusy(false);
    }
  }

  const segments = trip?.trip?.segments || [];
  const slack = slackMinutes(segments);
  const missedKind = events.some((event) => event.event === "disruption" && event.detail?.kind === "missed_connection");
  const cancelled = events.some((event) => event.event === "disruption" && event.detail?.kind === "cancellation");
  const rebooked = Boolean(trip?.trip?.rebooked);
  const missed = !rebooked && (missedKind || (slack !== null && slack < 40));
  const limit = board.max_fare_cents;
  const extNights = hotelExtensionNights(events);
  const firstCity = CITY[segments[0]?.origin] || segments[0]?.origin || "…";
  const lastCity = CITY[segments[segments.length - 1]?.destination] || segments[segments.length - 1]?.destination || "…";

  return (
    <main>
      <header>
        <div>
          <p className="kicker">Amex {trip?.trip?.passenger?.card || "Platinum Travel"} · 8 Oct 2026 · economy</p>
          <h1>
            {firstCity} to {lastCity}
          </h1>
          <p className="quiet">
            <select aria-label="Select trip" value={tripId} onChange={(e) => setTripId(e.target.value)}>
              {(trips.length ? trips : [{ id: tripId, name: "", route: "" }]).map((t) => (
                <option key={t.id} value={t.id}>
                  {t.name ? `${t.name} · ${t.route}` : t.id}
                </option>
              ))}
            </select>
          </p>
        </div>
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <span className="quiet">{live ? "● Live feed" : "○ polling"}</span>
          <div className={`pill ${state}`}>{state}</div>
        </div>
      </header>

      <section className="ticket">
        <div className="who">
          <div>
            <strong>{trip?.trip?.passenger?.name || "Ananya Sharma"}</strong>
            <span>
              {trip?.trip?.passenger?.card || "Platinum Travel"} ···· {trip?.trip?.passenger?.last4 || "4429"}
            </span>
          </div>
          <div>
            <span>PNR {trip?.trip?.passenger?.pnr || "K7H2QD"}</span>
            <span>Ticket {trip?.trip?.passenger?.ticket || "098 2148 831046"}</span>
          </div>
          <div>
            <span>{trip?.trip?.passenger?.phone || "+91 98100 44128"}</span>
            <span>{trip?.trip?.passenger?.transit || "US B1/B2 on file"}</span>
          </div>
        </div>
        <div className="scrub" aria-label="Time scrubber">
          <span>06:30 IST</span>
          <input
            type="range"
            min="0"
            max="150"
            value={scrub}
            onChange={(e) => setScrub(Number(e.target.value))}
            aria-label="Scrub departure morning"
          />
          <span>09:00 IST</span>
          <em>
            {(() => {
              const mins = 6 * 60 + 30 + scrub;
              const hh = String(Math.floor(mins / 60)).padStart(2, "0");
              const mm = String(mins % 60).padStart(2, "0");
              return `${hh}:${mm} IST`;
            })()}
            {scrub >= 85 ? " · board flips to Cancelled here" : " · board still On time here"}
          </em>
        </div>
        <p className="quiet">
          Scrubber sirf replay lens hai — board flip backend se hota hai (button 1 dabane pe). 07:55 IST
          pe le jao, wahi moment hai jab pehli flight cancel hoti hai aur agent chalta hai.
        </p>
        <div className="fids" aria-label="Departure board">
          {(rebooked ? segments : segments).map((segment, index) => {
            let status = "On time";
            if (!rebooked && index === 0 && cancelled) status = "Cancelled";
            if (!rebooked && index === 0 && missed) status = "Delayed";
            if (rebooked) status = "Reissued";
            return (
              <div className={`fids-row ${status.toLowerCase()}`} key={segment.id}>
                <strong>{segment.flight_number}</strong>
                <span>
                  {segment.origin}
                  {segment.terminal_origin ? ` ${segment.terminal_origin}` : ""} → {segment.destination}
                  {segment.terminal_destination ? ` ${segment.terminal_destination}` : ""}
                </span>
                <em>{status}</em>
              </div>
            );
          })}
        </div>
        <div className="track">
          {segments.map((segment, index) => (
            <div className="leg" key={segment.id}>
              <div className={`airport ${index === 0 && cancelled && !rebooked ? "struck" : ""}`}>
                <strong>
                  {segment.origin}
                  {segment.terminal_origin ? ` ${segment.terminal_origin}` : ""}
                </strong>
                <span>{CITY[segment.origin] || segment.origin}</span>
                <em>
                  {segment.airline ? `${segment.airline} ` : ""}
                  {segment.flight_number}
                </em>
                <time>
                  {localClock(segment.departure, segment.origin)} – {localClock(segment.arrival, segment.destination)}
                </time>
                <time>
                  {segment.aircraft || "Economy"}
                  {segment.seat ? ` · seat ${segment.seat}` : ""}
                </time>
              </div>
              {index === 0 && segments.length > 1 ? (
                <div className={`join ${missed ? "broken" : "ok"}`}>
                  <span>
                    {missed ? `${slack} min · missed` : `${slack} min`}
                    {segment.terminal_destination && segments[1].terminal_origin
                      ? ` · ${segment.terminal_destination}→${segments[1].terminal_origin}`
                      : ""}
                  </span>
                </div>
              ) : null}
            </div>
          ))}
          {segments.length > 0 ? (
            <div className="airport dest">
              <strong>
                {segments[segments.length - 1].destination}
                {segments[segments.length - 1].terminal_destination
                  ? ` ${segments[segments.length - 1].terminal_destination}`
                  : ""}
              </strong>
              <span>
                {CITY[segments[segments.length - 1].destination] || segments[segments.length - 1].destination}
              </span>
            </div>
          ) : null}
        </div>
        <p className="hotel">
          {trip?.trip?.hotel?.name || ""} · {trip?.trip?.hotel?.address || ""} · check-in 8 Oct ·
          checkout{" "}
          {trip?.trip?.hotel?.checkout
            ? addDays(trip.trip.hotel.checkout, extNights)
            : ""}{" "}
          · {trip?.trip?.hotel?.room || ""} · {rupees(trip?.trip?.hotel?.nightly_cents || 24000)} · conf{" "}
          {trip?.trip?.hotel?.confirmation || ""}
          {extNights > 0 ? ` · +${extNights} night extended` : ""}
        </p>
        <p className="quiet">Benefit fare cap {rupees(limit)} · bag 2 × 23 kg · member {trip?.trip?.passenger?.member_id || ""}</p>
        <p className="quiet">
          {rebooked
            ? `Plaza Premium Lounge, ${segments[0]?.origin || ""} ${segments[0]?.terminal_origin || ""} — void on cancel, reissued on ${segments[0]?.flight_number || "new flight"}.`
            : cancelled || missed
              ? `Plaza Premium Lounge, ${segments[0]?.origin || ""} ${segments[0]?.terminal_origin || ""} — void while disrupted.`
              : `Plaza Premium Lounge, ${segments[0]?.origin || ""} ${segments[0]?.terminal_origin || ""} — booked.`}
        </p>
        <div className="whatsapp">
          {(trip?.notifications || []).length === 0 ? (
            <p className="quiet">WhatsApp to {trip?.trip?.passenger?.phone || ""} stays quiet until a ticket actually changes.</p>
          ) : (
            (trip?.notifications || []).map((note) => (
              <p className="bubble" key={note.id}>
                {note.message}
              </p>
            ))
          )}
        </div>
      </section>

      <section>
        <h2>Legal fares it can book</h2>
        <p className="quiet">
          Sorted by delay, then extra fare. A US visa covers Heathrow and Frankfurt airside. It does not cover Canada, and it does not shrink a T2 to T5 walk.
        </p>
        <div className="options">
          {(board.options || []).map((option, index) => {
            const status = optionStatus(option.id, events);
            return (
              <article className={`fare ${status}`} key={option.id}>
                <header>
                  <span>#{index + 1}</span>
                  <em>{STATUS_LABEL[status]}</em>
                </header>
                <strong>{option.flight_numbers}</strong>
                <p>
                  {option.airline || "Economy"} · {CITY[option.origin] || option.origin} · {CITY[option.via] || option.via} ·{" "}
                  {CITY[option.destination] || option.destination}
                </p>
                <p className="quiet">{option.aircraft}{option.baggage ? ` · bag ${option.baggage}` : ""}</p>
                <p className="quiet">{benefitSplit(option.fare_delta_cents)}</p>
                <dl>
                  <div>
                    <dt>Later</dt>
                    <dd>{option.delay_minutes} min</dd>
                  </div>
                  <div>
                    <dt>Extra fare</dt>
                    <dd>{rupees(option.fare_delta_cents)}</dd>
                  </div>
                  <div>
                    <dt>Connect</dt>
                    <dd>{option.connection_minutes} min</dd>
                  </div>
                </dl>
              </article>
            );
          })}
        </div>
        <h2 className="reject-title">Rejected before anyone is charged</h2>
        <ul className="skipped">
          {(board.blocked || []).map((row) => (
            <li key={row.id}>
              <strong>
                {row.flight_numbers} · {rupees(row.fare_delta_cents)} · {row.delay_minutes} min later
              </strong>
              {row.reason}
            </li>
          ))}
        </ul>
      </section>

      <section className="steps">
        <h2>What it is doing</h2>
        <ol>
          {events.length === 0 ? (
            <li>
              Watching {segments[0]?.flight_number || ""} {segments[0]?.origin || ""}
              {segments[0]?.terminal_origin ? ` ${segments[0].terminal_origin}` : ""}–{segments[0]?.destination || ""}
              {segments[0]?.terminal_destination ? ` ${segments[0].terminal_destination}` : ""} and{" "}
              {segments[1]?.flight_number || ""}. Connection is {slack} minutes, including the terminal change.
            </li>
          ) : null}
          {events
            .filter((event) => event.event !== "authorize_allow")
            .map((event) => (
              <li key={event.id}>
                <strong>{sentence(event, segments)}</strong>
                <span>{event.state}</span>
              </li>
            ))}
        </ol>
      </section>

      <section>
        <h2>Past disruptions ({cases.length})</h2>
        {cases.length === 0 ? (
          <p className="quiet">Abhi koi disruption fire nahi hua. Button 1 ya 3 dabao, yahan history banegi.</p>
        ) : (
          <ul className="skipped">
            {cases.map((c) => (
              <li key={c.id}>
                <strong>
                  {c.id.slice(0, 8)} · {c.state}
                </strong>
                {new Date(c.created_at).toLocaleString("en-IN", { timeZone: "Asia/Kolkata" })}
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="panel">
        <button
          disabled={busy}
          onClick={() =>
            run(async () => {
              await resetAll();
              await disrupt("cancellation");
            })
          }
        >
          1. Cancel {segments[0]?.flight_number || "flight"}
        </button>
        <button
          disabled={busy}
          onClick={() =>
            run(async () => {
              await resetAll();
              await fetch(`${API}/v1/desk/fare-limit`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ trip_id: tripId, max_fare_cents: 10000 }),
              });
              await disrupt("cancellation");
            })
          }
        >
          2. Benefit cap ₹10,000
        </button>
        <button
          disabled={busy}
          onClick={() =>
            run(async () => {
              await resetAll();
              await disrupt("missed_connection");
            })
          }
        >
          3. Missed connection
        </button>
        <button disabled={busy} onClick={() => run(resetAll)}>
          Reset all trips
        </button>
        <div className="scrub" style={{ width: "100%" }} aria-label="Inbound delay slider">
          <span>Inbound delay</span>
          <input
            type="range"
            min="0"
            max="120"
            step="5"
            value={delayVal}
            onChange={(e) => setDelayVal(Number(e.target.value))}
            onMouseUp={() =>
              run(async () => {
                await resetAll();
                await disrupt("missed_connection", delayVal);
              })
            }
            onTouchEnd={() =>
              run(async () => {
                await resetAll();
                await disrupt("missed_connection", delayVal);
              })
            }
            aria-label="Fire inbound delay"
          />
          <em>{delayVal} min — chhodo to agent fire hoga</em>
        </div>
        {rebooked ? (
          <a href={`${API}/v1/trips/${tripId}/ics`}>
            <button type="button">Add {(segments[0]?.flight_number || "reissued").split("/")[0]} to calendar (.ics)</button>
          </a>
        ) : (
          <button type="button" disabled title="Booked hone ke baad .ics milega">
            Add to calendar (.ics)
          </button>
        )}
        <p>{hint}</p>
        <p className="quiet" style={{ width: "100%" }}>
          APIs: <code>GET /v1/trips</code> · <code>GET /v1/trips/{tripId}/board</code> ·{" "}
          <code>POST /v1/fare-quote</code> · <code>GET /v1/trips/{tripId}/stream</code> (SSE) ·{" "}
          <code>GET /v1/trips/{tripId}/ics</code> · <code>GET /v1/cases?trip_id={tripId}</code>
        </p>
      </section>
    </main>
  );
}
