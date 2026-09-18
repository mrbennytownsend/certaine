-- Real checklist items for Maroa Industrial Park, matching the documents
-- already seeded, plus a couple genuinely still outstanding, so the walker
-- has real gaps to find, not an empty list.

INSERT INTO checklist_items (deal_id, document_type, required, status, due_date)
VALUES
  ('22222222-2222-2222-2222-222222222222', 'rent_roll', true, 'flagged', '2025-07-20'),
  ('22222222-2222-2222-2222-222222222222', 't12', true, 'received', '2025-07-20'),
  ('22222222-2222-2222-2222-222222222222', 'entity_docs', true, 'requested', '2025-08-01'),
  ('22222222-2222-2222-2222-222222222222', 'insurance_cert', true, 'requested', '2025-08-10'),
  ('22222222-2222-2222-2222-222222222222', 'appraisal', true, 'requested', NULL);
