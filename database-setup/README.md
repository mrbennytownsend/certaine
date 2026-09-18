# Certaine — Database Setup

These 13 files build the real, working database from scratch. Verified
tonight to run clean, in this exact order, on a brand new Supabase project.

## Steps

1. Create a free project at supabase.com.
2. Go to the SQL Editor.
3. Run each file below, ONE AT A TIME, in this exact numeric order.
   Paste the whole file's contents, click Run, wait for success, then
   move to the next one. Don't skip ahead or combine files.

001_core_schema.sql
002_orgs_and_memory.sql
003_enable_rls.sql
004_seed_org_and_maroa.sql
005_milestones.sql
006_seed_checklist_items.sql
007_seed_remaining_deals.sql
008_responsible_parties.sql
009_lane_milestone_links.sql
010_deal_notes.sql
011_fix_demo_responsible_parties.sql
012_create_storage_bucket.sql
013_more_document_types.sql

## One real note on 012

012_create_storage_bucket.sql creates the real file storage bucket
("documents", private) used for uploaded PDFs and Excel files. If it
errors for any reason, you can instead create it manually: in Supabase,
go to Storage in the left sidebar, click "New bucket", name it exactly
"documents", leave "Public bucket" unchecked.

## After the database is set up

Copy your real Project URL and `service_role` key from Settings > API
into your own local `.env` file (see the main repo's README/code for
the full list of required environment variables, Supabase, Anthropic,
Twilio, Gmail). Never commit `.env` to Git.
