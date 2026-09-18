-- Enable RLS on every table. No policies defined yet on purpose:
-- with RLS on and zero policies, the default is deny-all for anon/authenticated
-- keys, which is exactly right until real user auth and per-org policies exist.
-- Your backend code should connect with the service_role key (bypasses RLS)
-- for all orchestration logic — never expose the service_role key client-side.

ALTER TABLE organizations       ENABLE ROW LEVEL SECURITY;
ALTER TABLE users               ENABLE ROW LEVEL SECURITY;
ALTER TABLE deals               ENABLE ROW LEVEL SECURITY;
ALTER TABLE parties             ENABLE ROW LEVEL SECURITY;
ALTER TABLE lanes               ENABLE ROW LEVEL SECURITY;
ALTER TABLE documents           ENABLE ROW LEVEL SECURITY;
ALTER TABLE checklist_items     ENABLE ROW LEVEL SECURITY;
ALTER TABLE messages            ENABLE ROW LEVEL SECURITY;
ALTER TABLE flags               ENABLE ROW LEVEL SECURITY;
ALTER TABLE contact_profiles    ENABLE ROW LEVEL SECURITY;
ALTER TABLE lender_profiles     ENABLE ROW LEVEL SECURITY;
ALTER TABLE benchmark_events    ENABLE ROW LEVEL SECURITY;

-- ============================================================
-- FUTURE STEP, not run here: once real user auth exists, add
-- per-org policies so a logged-in broker only sees their own
-- organization's deals, e.g.:
--
-- CREATE POLICY "org members see their own deals"
--   ON deals FOR SELECT
--   USING (broker_org_id IN (
--     SELECT org_id FROM users WHERE id = auth.uid()
--   ));
--
-- Leave commented out until users/auth are actually wired up —
-- writing a policy against a table with no real auth.uid() mapping
-- yet would either fail or accidentally allow nothing/everything.
-- ============================================================
