-- Seed data: one real org, one real deal, matching the Maroa Industrial Park
-- example used throughout the product spec and demo.
-- Plain SQL only — safe to paste directly into Supabase's SQL Editor.

INSERT INTO organizations (id, name, org_type) VALUES
  ('11111111-1111-1111-1111-111111111111', 'Sterling Capital', 'brokerage');

INSERT INTO users (org_id, name, email, role) VALUES
  ('11111111-1111-1111-1111-111111111111', 'Ben', 'ben@sterlingcapital.example', 'broker');

INSERT INTO deals (id, deal_number, name, deal_type, status, broker_org_id, target_close_date, closing_confidence, property_address)
VALUES
  ('22222222-2222-2222-2222-222222222222', '№0417', 'Maroa Industrial Park', 'debt', 'on_track',
   '11111111-1111-1111-1111-111111111111', '2025-08-28', 96, '1400 Maroa Ave, Industrial District');

INSERT INTO parties (deal_id, role, name, org_name, email, phone, preferred_channel, consent_basis)
VALUES
  ('22222222-2222-2222-2222-222222222222', 'sponsor', 'Maroa Holdings LLC', NULL, 'contact@maroaholdings.example', '555-0101', 'sms', 'informational_transactional'),
  ('22222222-2222-2222-2222-222222222222', 'lender_contact', 'Sarah Kim', 'Pacific Premier Bank', 'skim@ppb.example', '555-0102', 'email', 'informational_transactional'),
  ('22222222-2222-2222-2222-222222222222', 'title_company', 'Chicago Title', NULL, 'closings@chicagotitle.example', '555-0103', 'call', 'informational_transactional');

INSERT INTO lanes (deal_id, label, completion_pct, status) VALUES
  ('22222222-2222-2222-2222-222222222222', 'Lender A - Pacific Premier', 82, 'on_track'),
  ('22222222-2222-2222-2222-222222222222', 'Lender B - Kearny Bank', 55, 'on_track');

INSERT INTO documents (deal_id, document_type, status, extracted_fields)
VALUES
  ('22222222-2222-2222-2222-222222222222', 'rent_roll', 'flagged', '{"occupancy_pct": 91.2}'),
  ('22222222-2222-2222-2222-222222222222', 't12', 'received', '{"implied_occupancy_pct": 94.0}');

INSERT INTO flags (deal_id, severity, status, description)
SELECT '22222222-2222-2222-2222-222222222222', 'warning', 'open',
  'Occupancy differs 2.8% between rent roll (91.2%) and T-12 implied occupancy (94.0%)';
