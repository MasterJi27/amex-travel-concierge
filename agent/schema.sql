CREATE SCHEMA IF NOT EXISTS concierge;

CREATE TABLE IF NOT EXISTS concierge.snapshots (
  trip_id TEXT PRIMARY KEY,
  body TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS concierge.cases (
  id TEXT PRIMARY KEY,
  trip_id TEXT NOT NULL,
  state TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS concierge.case_events (
  id BIGSERIAL PRIMARY KEY,
  case_id TEXT NOT NULL,
  state TEXT NOT NULL,
  event TEXT NOT NULL,
  detail TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS case_events_case_id ON concierge.case_events (case_id, id);

CREATE TABLE IF NOT EXISTS concierge.notifications (
  id BIGSERIAL PRIMARY KEY,
  trip_id TEXT NOT NULL,
  message TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
