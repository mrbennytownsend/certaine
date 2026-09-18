-- Milestones: date-based contingencies and deadlines, distinct from documents.
-- A financing contingency isn't a file to chase, it's a countdown to track.
-- Run after 003_enable_rls.sql.

CREATE TYPE milestone_type AS ENUM (
  'financing_contingency', 'inspection_contingency', 'due_diligence_period',
  'appraisal_contingency', 'title_review_period', 'closing_date', 'other'
);
CREATE TYPE milestone_status AS ENUM ('pending', 'satisfied', 'waived', 'missed');

CREATE TABLE milestones (
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  deal_id           UUID NOT NULL REFERENCES deals(id) ON DELETE CASCADE,
  milestone_type    milestone_type NOT NULL,
  label             TEXT NOT NULL,               -- e.g. "Financing Contingency"
  due_date          DATE NOT NULL,
  status            milestone_status NOT NULL DEFAULT 'pending',
  side              TEXT,                          -- 'buyer' | 'seller' | NULL (applies to both/either)
  notes             TEXT,
  created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_milestones_deal ON milestones(deal_id);
CREATE INDEX idx_milestones_due_date ON milestones(due_date);

ALTER TABLE milestones ENABLE ROW LEVEL SECURITY;

-- Seed the milestones for the two existing demo deals, matching what's
-- already shown in the timeline/anticipate sections of the landing page.
INSERT INTO milestones (deal_id, milestone_type, label, due_date, status)
VALUES
  ('22222222-2222-2222-2222-222222222222', 'due_diligence_period', 'Due Diligence Period', '2025-08-05', 'pending'),
  ('22222222-2222-2222-2222-222222222222', 'closing_date', 'Closing', '2025-08-28', 'pending');
