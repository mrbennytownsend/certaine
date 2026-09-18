-- Real documents that actually show up in CRE closings but weren't in
-- the original fixed list, causing a real crash when Vera correctly
-- identified one (agency_disclosure) that the database didn't allow.

ALTER TYPE document_type ADD VALUE IF NOT EXISTS 'agency_disclosure';
ALTER TYPE document_type ADD VALUE IF NOT EXISTS 'lease_agreement';
ALTER TYPE document_type ADD VALUE IF NOT EXISTS 'property_condition_report';
ALTER TYPE document_type ADD VALUE IF NOT EXISTS 'lien_search';
ALTER TYPE document_type ADD VALUE IF NOT EXISTS 'zoning_report';
