-- Every checklist item on the four demo deals was seeded before
-- responsible_party_id existed, so none of them ever got assigned.
-- This is the real reason the "Draft a Follow-Up" button never appeared,
-- the code correctly hides it when there's no responsible party, and
-- every single one was genuinely null. Fixing all of them here, matched
-- to real parties already seeded for each deal.

-- Maroa Industrial Park
UPDATE checklist_items SET responsible_party_id = (
  SELECT id FROM parties WHERE deal_id = '22222222-2222-2222-2222-222222222222' AND role = 'sponsor'
) WHERE deal_id = '22222222-2222-2222-2222-222222222222' AND document_type IN ('rent_roll', 't12', 'entity_docs', 'insurance_cert');

UPDATE checklist_items SET responsible_party_id = (
  SELECT id FROM parties WHERE deal_id = '22222222-2222-2222-2222-222222222222' AND role = 'lender_contact'
) WHERE deal_id = '22222222-2222-2222-2222-222222222222' AND document_type = 'appraisal';

-- Cedar Point Storage
UPDATE checklist_items SET responsible_party_id = (
  SELECT id FROM parties WHERE deal_id = '33333333-3333-3333-3333-333333333333' AND role = 'buyer'
) WHERE deal_id = '33333333-3333-3333-3333-333333333333' AND document_type IN ('purchase_agreement', 'phase1_environmental');

UPDATE checklist_items SET responsible_party_id = (
  SELECT id FROM parties WHERE deal_id = '33333333-3333-3333-3333-333333333333' AND role = 'attorney'
) WHERE deal_id = '33333333-3333-3333-3333-333333333333' AND document_type = 'survey';

UPDATE checklist_items SET responsible_party_id = (
  SELECT id FROM parties WHERE deal_id = '33333333-3333-3333-3333-333333333333' AND role = 'lender_contact'
) WHERE deal_id = '33333333-3333-3333-3333-333333333333' AND document_type = 'appraisal';

-- 840 Redondo Retail
UPDATE checklist_items SET responsible_party_id = (
  SELECT id FROM parties WHERE deal_id = '44444444-4444-4444-4444-444444444444' AND role = 'buyer'
) WHERE deal_id = '44444444-4444-4444-4444-444444444444' AND document_type IN ('purchase_agreement', 'survey');

UPDATE checklist_items SET responsible_party_id = (
  SELECT id FROM parties WHERE deal_id = '44444444-4444-4444-4444-444444444444' AND role = 'attorney'
) WHERE deal_id = '44444444-4444-4444-4444-444444444444' AND document_type = 'estoppel';

-- Harbor Office Center (closed, but fixing for consistency)
UPDATE checklist_items SET responsible_party_id = (
  SELECT id FROM parties WHERE deal_id = '55555555-5555-5555-5555-555555555555' AND role = 'buyer'
) WHERE deal_id = '55555555-5555-5555-5555-555555555555';
