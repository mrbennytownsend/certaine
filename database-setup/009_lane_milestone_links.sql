-- Links each checklist item to the real milestone it satisfies (for the
-- milestone table's Documents column, which was hardcoded to a dash with
-- nothing real behind it). lane_id already existed in the original schema,
-- the real bug there was that intake.py never set it, not a missing column.

ALTER TABLE checklist_items
  ADD COLUMN milestone_id UUID REFERENCES milestones(id);

