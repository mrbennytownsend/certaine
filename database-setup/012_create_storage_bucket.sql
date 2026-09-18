-- Supabase Storage buckets are just rows in storage.buckets under the
-- hood, so this creates the real bucket via SQL instead of clicking
-- through the dashboard. public = false keeps it private, matching
-- what real, sensitive deal documents need.

INSERT INTO storage.buckets (id, name, public)
VALUES ('documents', 'documents', false);
