-- Real data for the three remaining deals, matching Maroa's structure.
-- Run this in Supabase's SQL Editor after everything else is already set up.

-- ============================================================
-- CEDAR POINT STORAGE (At Risk)
-- ============================================================
INSERT INTO deals (id, deal_number, name, deal_type, status, broker_org_id, target_close_date, closing_confidence, property_address)
VALUES ('33333333-3333-3333-3333-333333333333', '№0429', 'Cedar Point Storage', 'sales', 'at_risk',
  '11111111-1111-1111-1111-111111111111', '2026-09-10', 61, '220 Cedar Point Rd');

INSERT INTO parties (deal_id, role, name, org_name, email, phone, preferred_channel, consent_basis)
VALUES
  ('33333333-3333-3333-3333-333333333333', 'buyer', 'Cedar Point Partners LLC', NULL, 'contact@cedarpointpartners.example', '555-0201', 'email', 'informational_transactional'),
  ('33333333-3333-3333-3333-333333333333', 'lender_contact', 'Dana Alvarez', 'Regional Trust Bank', 'dalvarez@rtb.example', '555-0202', 'call', 'informational_transactional'),
  ('33333333-3333-3333-3333-333333333333', 'attorney', 'J. Ramirez', 'Buyer Counsel', 'jramirez@lawfirm.example', '555-0203', 'email', 'informational_transactional');

INSERT INTO lanes (deal_id, label, completion_pct, status) VALUES
  ('33333333-3333-3333-3333-333333333333', 'Regional Trust Bank', 58, 'at_risk');

INSERT INTO checklist_items (deal_id, document_type, required, status, due_date) VALUES
  ('33333333-3333-3333-3333-333333333333', 'purchase_agreement', true, 'received', '2026-07-28'),
  ('33333333-3333-3333-3333-333333333333', 'phase1_environmental', true, 'received', '2026-08-10'),
  ('33333333-3333-3333-3333-333333333333', 'survey', true, 'flagged', '2026-08-25'),
  ('33333333-3333-3333-3333-333333333333', 'appraisal', true, 'requested', '2026-08-30');

INSERT INTO milestones (deal_id, milestone_type, label, due_date, status) VALUES
  ('33333333-3333-3333-3333-333333333333', 'closing_date', 'Closing', '2026-09-10', 'pending'),
  ('33333333-3333-3333-3333-333333333333', 'appraisal_contingency', 'Appraisal', '2026-08-30', 'pending');

-- ============================================================
-- 840 REDONDO RETAIL (On Track)
-- ============================================================
INSERT INTO deals (id, deal_number, name, deal_type, status, broker_org_id, target_close_date, closing_confidence, property_address)
VALUES ('44444444-4444-4444-4444-444444444444', '№0421', '840 Redondo Retail', 'sales', 'on_track',
  '11111111-1111-1111-1111-111111111111', '2026-09-02', 93, '840 Redondo Ave');

INSERT INTO parties (deal_id, role, name, org_name, email, phone, preferred_channel, consent_basis)
VALUES
  ('44444444-4444-4444-4444-444444444444', 'buyer', 'Gotham RE Partners', NULL, 'contact@gothamre.example', '555-0301', 'email', 'informational_transactional'),
  ('44444444-4444-4444-4444-444444444444', 'attorney', 'R. Osei', 'Tenant Counsel', 'rosei@lawfirm.example', '555-0302', 'sms', 'informational_transactional');

INSERT INTO lanes (deal_id, label, completion_pct, status) VALUES
  ('44444444-4444-4444-4444-444444444444', 'Buyer Side', 93, 'on_track');

INSERT INTO checklist_items (deal_id, document_type, required, status, due_date) VALUES
  ('44444444-4444-4444-4444-444444444444', 'purchase_agreement', true, 'received', '2026-07-20'),
  ('44444444-4444-4444-4444-444444444444', 'survey', true, 'received', '2026-08-12'),
  ('44444444-4444-4444-4444-444444444444', 'estoppel', true, 'requested', '2026-08-28');

INSERT INTO milestones (deal_id, milestone_type, label, due_date, status) VALUES
  ('44444444-4444-4444-4444-444444444444', 'closing_date', 'Closing', '2026-09-02', 'pending');

-- ============================================================
-- HARBOR OFFICE CENTER (Closed)
-- ============================================================
INSERT INTO deals (id, deal_number, name, deal_type, status, broker_org_id, target_close_date, closing_confidence, property_address)
VALUES ('55555555-5555-5555-5555-555555555555', '№0433', 'Harbor Office Center', 'sales', 'closed',
  '11111111-1111-1111-1111-111111111111', '2026-07-15', 100, '12 Harbor Way');

INSERT INTO parties (deal_id, role, name, org_name, email, phone, preferred_channel, consent_basis)
VALUES ('55555555-5555-5555-5555-555555555555', 'buyer', 'Metro Capital Group', NULL, 'contact@metrocapital.example', '555-0401', 'email', 'informational_transactional');

INSERT INTO lanes (deal_id, label, completion_pct, status) VALUES
  ('55555555-5555-5555-5555-555555555555', 'Metro Capital', 100, 'on_track');

INSERT INTO checklist_items (deal_id, document_type, required, status, due_date) VALUES
  ('55555555-5555-5555-5555-555555555555', 'purchase_agreement', true, 'received', '2026-06-01'),
  ('55555555-5555-5555-5555-555555555555', 'closing_statement', true, 'received', '2026-07-15');

INSERT INTO milestones (deal_id, milestone_type, label, due_date, status) VALUES
  ('55555555-5555-5555-5555-555555555555', 'closing_date', 'Closing', '2026-07-15', 'satisfied');
