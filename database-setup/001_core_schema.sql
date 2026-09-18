-- Certaine core schema
-- Models the entities from the product spec: Deal, Party, Lane, ChecklistItem, Document, Message, Flag
-- Postgres. Run in order. Assumes pgcrypto for gen_random_uuid() (or swap for uuid-ossp).

CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ============================================================
-- DEALS
-- One row per transaction. deal_type distinguishes debt vs sales,
-- which is what determines which checklist template gets loaded.
-- ============================================================
CREATE TYPE deal_type AS ENUM ('debt', 'sales');
CREATE TYPE deal_status AS ENUM ('on_track', 'at_risk', 'stalled', 'closed', 'dead');

CREATE TABLE deals (
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  deal_number       TEXT UNIQUE NOT NULL,          -- human-facing id, e.g. "№0417"
  name              TEXT NOT NULL,                  -- e.g. "Maroa Industrial Park"
  deal_type         deal_type NOT NULL,
  status            deal_status NOT NULL DEFAULT 'on_track',
  broker_org_id     UUID NOT NULL,                  -- FK to the brokerage/customer account, added in a later migration
  target_close_date DATE,
  closing_confidence SMALLINT CHECK (closing_confidence BETWEEN 0 AND 100),
  property_address  TEXT,
  deal_value_cents  BIGINT,                         -- for bps-based pricing later; store cents, avoid float math
  created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_deals_status ON deals(status);
CREATE INDEX idx_deals_broker_org ON deals(broker_org_id);

-- ============================================================
-- PARTIES
-- Any human or entity involved in a deal: sponsor, buyer, seller,
-- lender contact, attorney, title co, inspector, etc.
-- Consent fields are here specifically for TCPA compliance —
-- every contact needs a documented basis before Vera can text/call them.
-- ============================================================
CREATE TYPE party_role AS ENUM (
  'sponsor', 'buyer', 'seller', 'lender_contact', 'attorney',
  'title_company', 'surveyor', 'inspector', 'property_manager',
  'tenant', 'broker', 'other'
);

CREATE TYPE consent_basis AS ENUM ('informational_transactional', 'express_written', 'unverified');
CREATE TYPE preferred_channel AS ENUM ('sms', 'email', 'call', 'unknown');

CREATE TABLE parties (
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  deal_id           UUID NOT NULL REFERENCES deals(id) ON DELETE CASCADE,
  role              party_role NOT NULL,
  name              TEXT NOT NULL,
  org_name          TEXT,                           -- e.g. "Chicago Title", "Pacific Premier Bank"
  email             TEXT,
  phone             TEXT,
  preferred_channel preferred_channel NOT NULL DEFAULT 'unknown',
  consent_basis     consent_basis NOT NULL DEFAULT 'unverified',
  consent_source    TEXT,                           -- how/when consent was obtained, for the audit trail
  do_not_contact    BOOLEAN NOT NULL DEFAULT false,  -- opt-out flag, must be checked before any outbound contact
  created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_parties_deal ON parties(deal_id);
CREATE INDEX idx_parties_dnc ON parties(do_not_contact) WHERE do_not_contact = true;

-- ============================================================
-- LANES
-- Debt deals only: one lane per lender in play, so a broker
-- shopping to 3-5 lenders can see each lane's progress independently.
-- Sales deals typically have a single implicit lane (buyer-side),
-- represented as one lane row with lender_party_id NULL.
-- ============================================================
CREATE TABLE lanes (
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  deal_id           UUID NOT NULL REFERENCES deals(id) ON DELETE CASCADE,
  lender_party_id   UUID REFERENCES parties(id),     -- NULL for a sales-side single lane
  label             TEXT NOT NULL,                   -- "Lender A", "Buyer Side", etc.
  completion_pct    SMALLINT NOT NULL DEFAULT 0 CHECK (completion_pct BETWEEN 0 AND 100),
  status            deal_status NOT NULL DEFAULT 'on_track',
  created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_lanes_deal ON lanes(deal_id);

-- ============================================================
-- DOCUMENTS
-- Every file associated with a deal, classified by type,
-- with structured extracted fields for cross-document reconciliation
-- (e.g. comparing T-12 NOI against rent roll implied income).
-- ============================================================
CREATE TYPE document_status AS ENUM ('requested', 'received', 'verified', 'flagged');
CREATE TYPE document_type AS ENUM (
  'term_sheet', 'rent_roll', 't12', 'pfs', 'appraisal', 'snda', 'entity_docs',
  'insurance_cert', 'purchase_agreement', 'title_commitment', 'survey',
  'estoppel', 'phase1_environmental', 'tenant_notice', 'closing_statement', 'other'
);

CREATE TABLE documents (
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  deal_id           UUID NOT NULL REFERENCES deals(id) ON DELETE CASCADE,
  lane_id           UUID REFERENCES lanes(id),        -- NULL if shared across all lanes (e.g. title, survey)
  document_type     document_type NOT NULL,
  status            document_status NOT NULL DEFAULT 'requested',
  file_url          TEXT,                              -- pointer to blob storage, not the file itself
  extracted_fields  JSONB,                              -- structured extraction output, shape varies by document_type
  classification_confidence NUMERIC(4,3),                -- 0.000–1.000, how sure the classifier was
  version           INT NOT NULL DEFAULT 1,
  received_at       TIMESTAMPTZ,
  requested_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_documents_deal ON documents(deal_id);
CREATE INDEX idx_documents_status ON documents(status);

-- ============================================================
-- CHECKLIST ITEMS
-- The per-lane (or per-deal, for sales) required-document tracker
-- that the dashboard's checklist/swimlane views read from directly.
-- ============================================================
CREATE TABLE checklist_items (
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  deal_id           UUID NOT NULL REFERENCES deals(id) ON DELETE CASCADE,
  lane_id           UUID REFERENCES lanes(id),
  document_type     document_type NOT NULL,
  required          BOOLEAN NOT NULL DEFAULT true,
  document_id       UUID REFERENCES documents(id),     -- linked once satisfied
  status            document_status NOT NULL DEFAULT 'requested',
  due_date          DATE,
  created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_checklist_deal ON checklist_items(deal_id);
CREATE INDEX idx_checklist_lane ON checklist_items(lane_id);

-- ============================================================
-- MESSAGES
-- Every communication Vera sends or receives, across every channel.
-- This is the audit trail: full transcripts, in the broker's name,
-- visible any time — required both for trust and for TCPA compliance.
-- ============================================================
CREATE TYPE message_channel AS ENUM ('sms', 'email', 'call', 'slack');
CREATE TYPE message_direction AS ENUM ('outbound', 'inbound');

CREATE TABLE messages (
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  deal_id           UUID NOT NULL REFERENCES deals(id) ON DELETE CASCADE,
  party_id          UUID REFERENCES parties(id),       -- NULL for internal (Slack/team) messages
  channel           message_channel NOT NULL,
  direction         message_direction NOT NULL,
  body              TEXT,                               -- transcript text; for calls, this is the transcript
  recording_url      TEXT,                               -- for calls specifically
  sent_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
  -- compliance metadata, required for every outbound sms/call:
  consent_checked   BOOLEAN NOT NULL DEFAULT false,
  quiet_hours_ok    BOOLEAN NOT NULL DEFAULT false
);

CREATE INDEX idx_messages_deal ON messages(deal_id);
CREATE INDEX idx_messages_party ON messages(party_id);
CREATE INDEX idx_messages_sent_at ON messages(sent_at);

-- ============================================================
-- FLAGS
-- Any discrepancy or exception Vera raises: a T-12/rent-roll
-- mismatch, a wrong signer on an estoppel, a stale document.
-- Resolution status here is what the dashboard's "at risk" badges read.
-- ============================================================
CREATE TYPE flag_severity AS ENUM ('info', 'warning', 'urgent');
CREATE TYPE flag_status AS ENUM ('open', 'escalated_to_broker', 'resolved');

CREATE TABLE flags (
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  deal_id           UUID NOT NULL REFERENCES deals(id) ON DELETE CASCADE,
  document_id       UUID REFERENCES documents(id),
  checklist_item_id UUID REFERENCES checklist_items(id),
  severity          flag_severity NOT NULL DEFAULT 'warning',
  status            flag_status NOT NULL DEFAULT 'open',
  description       TEXT NOT NULL,                      -- e.g. "Occupancy differs 2.8% between rent roll and T-12"
  raised_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
  resolved_at       TIMESTAMPTZ,
  resolution_note   TEXT
);

CREATE INDEX idx_flags_deal ON flags(deal_id);
CREATE INDEX idx_flags_status ON flags(status);

-- ============================================================
-- updated_at trigger for deals (kept minimal; extend to other
-- tables as needed once the app layer is in place)
-- ============================================================
CREATE OR REPLACE FUNCTION set_updated_at() RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_deals_updated_at
BEFORE UPDATE ON deals
FOR EACH ROW EXECUTE FUNCTION set_updated_at();
