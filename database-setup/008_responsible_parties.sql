-- Links each checklist item to the real party responsible for providing it.
-- Without this, Vera knows a rent roll is missing but not who to ask for it.

ALTER TABLE checklist_items
  ADD COLUMN responsible_party_id UUID REFERENCES parties(id);

-- Also track whether a human has actually reviewed and approved a party
-- before Vera is allowed to contact them, separate from consent_basis
-- (which is about the legal basis for contact). This is the "someone
-- actually looked at this extracted party and confirmed it's right" flag.
ALTER TABLE parties
  ADD COLUMN reviewed_by_human BOOLEAN NOT NULL DEFAULT false;

-- The parties already seeded for Maroa, Cedar Point, Redondo, and Harbor
-- were manually set up and already tested against, mark them reviewed so
-- this new gate only affects genuinely new, unverified extractions.
UPDATE parties SET reviewed_by_human = true
WHERE deal_id IN (
  '22222222-2222-2222-2222-222222222222',
  '33333333-3333-3333-3333-333333333333',
  '44444444-4444-4444-4444-444444444444',
  '55555555-5555-5555-5555-555555555555'
);
