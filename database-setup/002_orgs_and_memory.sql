-- Organizations, users, and the memory layer.
-- Run after 001_core_schema.sql.

-- ============================================================
-- ORGANIZATIONS
-- A brokerage, TC agency, or lender ops team, the paying account.
-- ============================================================
CREATE TABLE organizations (
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name              TEXT NOT NULL,
  org_type          TEXT NOT NULL DEFAULT 'brokerage',  -- 'brokerage' | 'tc_agency' | 'lender_ops'
  pricing_plan      TEXT NOT NULL DEFAULT 'pilot',       -- 'pilot' | 'per_deal' | 'hybrid' | 'bps'
  created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE users (
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id            UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  name              TEXT NOT NULL,
  email             TEXT UNIQUE NOT NULL,
  role              TEXT NOT NULL DEFAULT 'coordinator',  -- 'coordinator' | 'broker' | 'admin'
  created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Now that organizations exists, wire up the FK left dangling in 001:
ALTER TABLE deals
  ADD CONSTRAINT fk_deals_broker_org
  FOREIGN KEY (broker_org_id) REFERENCES organizations(id);

-- ============================================================
-- MEMORY LAYER
-- This is what makes "she's worked three deals with this attorney
-- before" a real, queryable fact instead of a line of marketing copy.
--
-- contact_profiles: cross-deal knowledge about a specific person or
-- org Vera has dealt with before, regardless of which deal they show
-- up on next time. Keyed on email/phone, not party_id, since a party
-- row is scoped to one deal but a contact is a real person across many.
-- ============================================================
CREATE TABLE contact_profiles (
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  broker_org_id     UUID NOT NULL REFERENCES organizations(id),
  identifying_email TEXT,
  identifying_phone TEXT,
  display_name      TEXT NOT NULL,
  org_name          TEXT,
  preferred_channel preferred_channel,                 -- learned over time, not asked once
  avg_response_time_hours NUMERIC(6,2),
  notes             TEXT,                               -- freeform: "prefers calls, slow on entity docs"
  deals_seen_count  INT NOT NULL DEFAULT 0,
  last_seen_at      TIMESTAMPTZ,
  created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (broker_org_id, identifying_email)
);

CREATE INDEX idx_contact_profiles_org ON contact_profiles(broker_org_id);

-- Links a deal-scoped party to the persistent cross-deal contact,
-- so "the same attorney, third deal" is a real join, not a guess.
ALTER TABLE parties
  ADD COLUMN contact_profile_id UUID REFERENCES contact_profiles(id);

-- ============================================================
-- LENDER PROFILES
-- Cross-deal knowledge about a specific lender's typical checklist,
-- turnaround time, and quirks — the data asset that lets Vera front-load
-- a document request before a lender even asks for it.
-- ============================================================
CREATE TABLE lender_profiles (
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  lender_name       TEXT NOT NULL UNIQUE,
  typical_checklist JSONB,                               -- default document_type list this lender usually wants
  avg_turnaround_days NUMERIC(5,2),
  notes             TEXT,
  deals_seen_count  INT NOT NULL DEFAULT 0,
  last_seen_at      TIMESTAMPTZ,
  created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ============================================================
-- BENCHMARK EVENTS
-- Append-only log feeding the future benchmarking-data product:
-- typical timelines, which lenders run slow, by asset class/market.
-- Kept deliberately generic and anonymizable (no PII beyond what's
-- already in the linked deal) so it can be aggregated safely later.
-- ============================================================
CREATE TABLE benchmark_events (
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  deal_id           UUID NOT NULL REFERENCES deals(id) ON DELETE CASCADE,
  event_type        TEXT NOT NULL,                       -- 'document_received' | 'lane_closed' | 'deal_closed' | etc.
  document_type     document_type,
  days_from_request NUMERIC(6,2),
  market            TEXT,                                 -- e.g. metro area, for later benchmarking cuts
  asset_class       TEXT,                                 -- 'industrial' | 'retail' | 'office' | 'multifamily' | etc.
  occurred_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_benchmark_events_type ON benchmark_events(event_type);
