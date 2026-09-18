-- A simple, real place to write things down that aren't structured data
-- or a message that actually went out. Every real CRM has this, nothing
-- in Certaine did until now.

ALTER TABLE deals
  ADD COLUMN notes TEXT;
