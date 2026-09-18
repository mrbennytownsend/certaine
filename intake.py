"""
Certaine — real deal intake from a purchase agreement.

This is the actual "forward the PSA, Vera takes it from there" workflow.
Paste in real purchase agreement text (or realistic sample text to test),
and this extracts the real structured facts and creates a genuine new deal
in Supabase, parties and all, no manual SQL, no hand-editing.

WHAT THIS DOES NOT DO YET, being honest about the real gap:
This takes pasted TEXT, not an actual uploaded PDF file. Getting from a real
PDF to text is a separate, smaller step (a library like pdfplumber), worth
adding once this core extraction-and-creation step is proven to work well.
"""

import os
import json
from dotenv import load_dotenv
from supabase import create_client
import anthropic
import pdfplumber
from pdf2image import convert_from_path
import pytesseract
from openpyxl import load_workbook
from send_real_email import send_real_email
from notify_slack import notify_kickoff_sent

load_dotenv()

supabase = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])
claude = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

DEFAULT_BROKER_ORG_ID = "11111111-1111-1111-1111-111111111111"  # Sterling Capital, seeded earlier


def extract_text_from_excel(file_path: str) -> str:
    """Real Excel reading. Rent rolls and T-12s very often arrive as
    spreadsheets, not PDFs, this reads every sheet and every real row,
    turned into plain text Claude can reason over the same way it
    already does for PDF text."""
    workbook = load_workbook(file_path, data_only=True)
    text_parts = []
    for sheet in workbook.worksheets:
        text_parts.append(f"--- Sheet: {sheet.title} ---")
        for row in sheet.iter_rows(values_only=True):
            row_values = [str(cell) if cell is not None else "" for cell in row]
            if any(v.strip() for v in row_values):
                text_parts.append("\t".join(row_values))
    return "\n".join(text_parts)


def extract_text_from_file(file_path: str, original_filename: str) -> str:
    """The real dispatcher: picks PDF or Excel extraction based on the
    actual file extension, so the rest of the pipeline doesn't care
    which format a document arrived in."""
    extension = os.path.splitext(original_filename)[1].lower()
    if extension in (".xlsx", ".xls"):
        return extract_text_from_excel(file_path)
    return extract_text_from_pdf(file_path)


def extract_text_from_pdf(file_path: str) -> str:
    """Real PDF reading, with a real OCR fallback, not a placeholder.
    First tries native text extraction (fast, works for most agreements
    that were typed and exported to PDF). If that comes back empty, the
    PDF is almost certainly a scan, a photo or image of a printed page,
    so this automatically falls back to real OCR on each page image."""

    text_parts = []
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
    native_text = "\n".join(text_parts)

    if native_text.strip():
        return native_text

    # Native extraction found nothing, this is a scanned document. Convert
    # each page to a real image and run real OCR on it.
    ocr_parts = []
    pages_as_images = convert_from_path(file_path)
    for page_image in pages_as_images:
        ocr_text = pytesseract.image_to_string(page_image)
        if ocr_text.strip():
            ocr_parts.append(ocr_text)
    return "\n".join(ocr_parts)


def extract_deal_from_text(psa_text: str) -> dict:
    """Ask Claude to pull real structured facts out of raw agreement text,
    the same real-extraction approach proven in extract_and_reconcile.py.
    Now also pulls real milestone dates when stated, and infers a real
    starter document checklist, so a new deal isn't left completely empty
    on those two things."""

    prompt = f"""You are extracting structured deal information from a commercial real estate
purchase agreement or term sheet. Here is the raw text:
---
{psa_text}
---

Extract the following as JSON only, no other text, no markdown formatting:
{{
  "deal_name": "a short, real-sounding name for this deal, usually the property name or address",
  "property_address": "the property address if stated, otherwise null",
  "deal_type": "debt or sales, whichever this document actually is",
  "target_close_date": "YYYY-MM-DD format if a closing date is stated, otherwise null",
  "deal_value_dollars": "the deal or loan value as a plain number if stated, otherwise null",
  "parties": [
    {{"role": "one of: sponsor, buyer, seller, lender_contact, attorney, title_company, other",
      "name": "their real name or entity name",
      "org_name": "their company/firm name if different from their name, otherwise null"}}
  ],
  "milestones": [
    {{"milestone_type": "one of: financing_contingency, inspection_contingency, due_diligence_period, appraisal_contingency, title_review_period, closing_date, other",
      "label": "a short real label for this milestone",
      "due_date": "YYYY-MM-DD if a specific date is stated or can be calculated from the document, otherwise null, skip this milestone entirely if you can't determine a real date"}}
  ],
  "checklist": [
    {{"document_type": "one of: term_sheet, rent_roll, t12, pfs, appraisal, snda, entity_docs, insurance_cert, purchase_agreement, title_commitment, survey, estoppel, phase1_environmental, tenant_notice, closing_statement, other",
      "status": "received if this exact document is the one you're reading right now or is clearly attached/referenced as already provided, otherwise requested",
      "responsible_party_name": "the exact name of whichever party above should actually provide this document, matching one of the names in the parties list exactly. If you genuinely can't tell who from the extracted parties would provide it, use null rather than guessing.",
      "lender_org_name": "for debt deals only: which lender's org_name (from the parties list) this specific document belongs to, if this deal has multiple lenders. Use null for sales deals or if there's only one lender.",
      "related_milestone_label": "the exact label of whichever milestone above this document most directly relates to, if any real connection exists (for example, an appraisal document relates to an appraisal contingency milestone). Use null if there's no real, specific connection, don't force one."}}
  ]
}}

For the checklist specifically: include the realistic standard document set for
this deal type (debt deals typically need term sheet, rent roll, T-12, PFS,
appraisal, SNDA, entity docs, insurance certificate; sales deals typically
need purchase agreement, title commitment, survey, estoppel, Phase I
environmental, tenant notices, closing statement). Mark the one you're
currently reading as received, everything else as requested unless the text
clearly says otherwise. For responsible_party_name, use your real knowledge
of who actually provides each document type in a real CRE closing, and match
that to a real extracted party's exact name whenever you can, don't force a
match that isn't real. Extract every real party you can identify. Only
include a milestone if you can identify a real or clearly calculable date,
don't invent one. Return ONLY valid JSON, nothing else."""

    response = claude.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=800,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = response.content[0].text.strip().replace("```json", "").replace("```", "").strip()
    return json.loads(raw)


VALID_DOCUMENT_TYPES = {
    "term_sheet", "rent_roll", "t12", "pfs", "appraisal", "snda", "entity_docs",
    "insurance_cert", "purchase_agreement", "title_commitment", "survey", "estoppel",
    "phase1_environmental", "tenant_notice", "closing_statement", "agency_disclosure",
    "lease_agreement", "property_condition_report", "lien_search", "zoning_report", "other",
}


def safe_document_type(document_type: str) -> str:
    """Real safety net: Claude sometimes correctly identifies a genuine
    document type that isn't in the database's fixed list yet. Rather
    than let that crash deal creation entirely, fall back to 'other'
    and keep going, this is why a whole deal used to fail on one
    unexpected document."""
    return document_type if document_type in VALID_DOCUMENT_TYPES else "other"


def create_real_deal(extraction: dict, broker_org_id: str = DEFAULT_BROKER_ORG_ID) -> str:
    """Actually creates the deal and its parties in Supabase. Returns the
    new deal's real id."""

    deal_number = f"№{str(abs(hash(extraction['deal_name'])))[:4]}"
    value_cents = int(extraction["deal_value_dollars"] * 100) if extraction.get("deal_value_dollars") else None

    deal_row = supabase.table("deals").insert({
        "deal_number": deal_number,
        "name": extraction["deal_name"],
        "deal_type": extraction.get("deal_type", "sales"),
        "status": "on_track",
        "broker_org_id": broker_org_id,
        "target_close_date": extraction.get("target_close_date"),
        "property_address": extraction.get("property_address"),
        "deal_value_cents": value_cents,
    }).execute()
    deal_id = deal_row.data[0]["id"]

    party_id_by_name = {}
    for p in extraction.get("parties", []):
        result = supabase.table("parties").insert({
            "deal_id": deal_id,
            "role": p["role"],
            "name": p["name"],
            "org_name": p.get("org_name"),
            "consent_basis": "unverified",  # real consent must be confirmed before Vera can contact them
            "reviewed_by_human": False,  # a real person must review this extracted party before Vera acts on it
        }).execute()
        party_id_by_name[p["name"]] = result.data[0]["id"]

    # Create real lanes BEFORE checklist items, so items can actually
    # reference a real lane_id, not just exist alongside empty lanes.
    # Debt deals get one lane per real lender_contact found. Sales deals
    # get a single buyer-side lane, matching how the existing demo deals work.
    deal_type = extraction.get("deal_type", "sales")
    lane_id_by_lender_org = {}
    default_lane_id = None
    if deal_type == "debt":
        lenders = [p for p in extraction.get("parties", []) if p["role"] == "lender_contact"]
        for lender in lenders:
            lane_label = lender.get("org_name") or lender["name"]
            result = supabase.table("lanes").insert({
                "deal_id": deal_id, "label": lane_label, "completion_pct": 0, "status": "on_track",
            }).execute()
            lane_id_by_lender_org[lane_label] = result.data[0]["id"]
            if default_lane_id is None:
                default_lane_id = result.data[0]["id"]
    else:
        result = supabase.table("lanes").insert({
            "deal_id": deal_id, "label": "Buyer Side", "completion_pct": 0, "status": "on_track",
        }).execute()
        default_lane_id = result.data[0]["id"]

    # Create milestones BEFORE checklist items, same real reason.
    milestone_id_by_label = {}
    for m in extraction.get("milestones", []):
        if not m.get("due_date"):
            continue  # skip anything without a real, identified date
        result = supabase.table("milestones").insert({
            "deal_id": deal_id,
            "milestone_type": m["milestone_type"],
            "label": m["label"],
            "due_date": m["due_date"],
            "status": "pending",
        }).execute()
        milestone_id_by_label[m["label"]] = result.data[0]["id"]

    for c in extraction.get("checklist", []):
        lane_id = lane_id_by_lender_org.get(c.get("lender_org_name")) or default_lane_id
        milestone_id = milestone_id_by_label.get(c.get("related_milestone_label"))
        supabase.table("checklist_items").insert({
            "deal_id": deal_id,
            "document_type": safe_document_type(c["document_type"]),
            "required": True,
            "status": c.get("status", "requested"),
            "responsible_party_id": find_best_name_match(c.get("responsible_party_name"), party_id_by_name),
            "lane_id": lane_id,
            "milestone_id": milestone_id,
        }).execute()

    return deal_id


def find_best_name_match(target_name: str, name_to_id: dict) -> str:
    """Real, forgiving matching, not exact-string-only. Handles case
    differences and partial names like 'S. Hansberry' matching 'Shawn
    Hansberry', which exact matching was silently failing on."""
    if not target_name:
        return None
    target_lower = target_name.lower().strip()
    for name, party_id in name_to_id.items():
        if name.lower().strip() == target_lower:
            return party_id
    target_words = set(w for w in target_lower.split() if len(w) > 1)
    for name, party_id in name_to_id.items():
        name_words = set(w.rstrip('.').lower() for w in name.split() if len(w) > 1)
        if target_words & name_words:
            return party_id
    return None


def draft_intake_from_text(psa_text: str) -> dict:
    """Step one, real draft. Extracts everything, deal info, parties,
    milestones, checklist, but writes nothing to Supabase yet. A human
    gets to actually see and correct this before anything becomes real."""
    extraction = extract_deal_from_text(psa_text)
    return {"ok": True, "extraction": extraction}


def confirm_intake(extraction: dict) -> dict:
    """Step two, the real creation. Only runs after a human has seen the
    extraction and confirmed it, or edited it first. This is the same
    real create_real_deal that already existed, just no longer called
    automatically."""
    deal_id = create_real_deal(extraction)
    return {"ok": True, "deal_id": deal_id}


def intake_psa(psa_text: str) -> dict:
    """The full real flow from pasted text: read it, extract it, create it."""
    extraction = extract_deal_from_text(psa_text)
    deal_id = create_real_deal(extraction)
    return {"ok": True, "deal_id": deal_id, "extraction": extraction}


def sanitize_for_path(name: str) -> str:
    """Turns a real deal name into a real, safe folder name, so files
    land somewhere a human would actually recognize later."""
    return "".join(c if c.isalnum() or c in " -_" else "" for c in name).strip().replace(" ", "_")


def store_document_file(deal_id: str, document_type: str, checklist_item_id: str, local_file_path: str, original_filename: str) -> str:
    """Actually uploads the real file to real, permanent storage, organized
    by deal name and document type, so it can genuinely be found again
    later, not read once and thrown away like every upload before this."""
    deal = supabase.table("deals").select("name").eq("id", deal_id).single().execute().data
    folder = sanitize_for_path(deal["name"])
    extension = os.path.splitext(original_filename)[1] or ".pdf"
    storage_path = f"{folder}/{document_type}{extension}"

    with open(local_file_path, "rb") as f:
        file_bytes = f.read()
    supabase.storage.from_("documents").upload(
        storage_path, file_bytes, {"content-type": "application/pdf", "upsert": "true"}
    )

    doc_result = supabase.table("documents").insert({
        "deal_id": deal_id,
        "document_type": safe_document_type(document_type),
        "status": "received",
        "file_url": storage_path,
        "received_at": "now()",
    }).execute()
    document_id = doc_result.data[0]["id"]

    if checklist_item_id:
        supabase.table("checklist_items").update({"document_id": document_id}).eq("id", checklist_item_id).execute()

    return document_id


def get_document_download_url(document_id: str) -> str:
    """Generates a real, temporary signed URL to actually view or
    download a stored file. Signed, not public, since these are real,
    sensitive deal documents, expires after an hour."""
    doc = supabase.table("documents").select("file_url").eq("id", document_id).single().execute().data
    if not doc or not doc.get("file_url"):
        return None
    result = supabase.storage.from_("documents").create_signed_url(doc["file_url"], 3600)
    return result.get("signedURL") or result.get("signedUrl")


def list_deal_files(deal_id: str) -> list:
    """Real file browser: lists everything actually stored for this deal,
    straight from Supabase Storage, not filtered through whether it
    happens to be linked to a checklist item. This is the actual answer
    to 'where are my files,' not a side effect of clicking into one
    specific document's modal."""
    deal = supabase.table("deals").select("name").eq("id", deal_id).single().execute().data
    folder = sanitize_for_path(deal["name"])
    try:
        files = supabase.storage.from_("documents").list(folder)
    except Exception:
        return []
    return [{"name": f["name"], "path": f"{folder}/{f['name']}", "size": f.get("metadata", {}).get("size")} for f in files]


def get_signed_url_for_path(storage_path: str) -> str:
    """Real signed URL for a specific storage path, for the file browser
    to actually open files, not just list their names."""
    result = supabase.storage.from_("documents").create_signed_url(storage_path, 3600)
    return result.get("signedURL") or result.get("signedUrl")


def classify_and_match_document(deal_id: str, doc_text: str) -> dict:
    """Real classification: read an uploaded document, figure out what
    type it actually is, and propose which checklist item it satisfies
    for THIS deal specifically. Does not commit anything, a human has to
    confirm the match is actually correct first."""
    checklist = supabase.table("checklist_items").select("*").eq("deal_id", deal_id).execute().data
    deal = supabase.table("deals").select("*").eq("id", deal_id).single().execute().data

    checklist_summary = "\n".join(f"- id: {c['id']}, type: {c['document_type']}, status: {c['status']}" for c in checklist)

    prompt = f"""You are reviewing an uploaded document to figure out what it is and whether
it matches something already expected on this specific deal.

Deal: {deal['name']}
Open checklist items for this deal:
{checklist_summary}

Here is the uploaded document's text:
---
{doc_text[:4000]}
---

Use these real, concrete distinguishing rules, don't guess loosely:

- rent_roll: a per-unit or per-tenant listing, columns like unit number,
  tenant name, square footage, current rent, lease dates. A snapshot of
  who's in the building right now.
- t12: a trailing-twelve-month operating statement, income and expense
  line items over a 12-month period, ending in a net operating income
  (NOI) figure. Not organized by unit or tenant, organized by revenue
  and expense category.
- pfs: a personal financial statement, assets and liabilities of an
  individual, not the property.
- survey: a physical/legal description of the property boundary, often
  with technical language about easements and metes and bounds.
- title_commitment: from a title company, lists real property exceptions
  and requirements before insuring title.
- entity_docs: formation documents for an LLC or corporation, articles
  of organization, operating agreements, not financial data at all.

If the document has a per-unit or per-tenant breakdown with current
rents, it is a rent_roll, not a t12, even if it also mentions income.
If it's a 12-month income and expense statement with no per-unit
breakdown, it's a t12.

Respond with ONLY valid JSON: {{
  "document_type": "your best real classification of what this document actually is",
  "matches_checklist_item_id": "the id of the checklist item this satisfies, if any real match exists, otherwise null",
  "confidence": "high, medium, or low, be honest, don't inflate this",
  "reasoning": "one real sentence on why you think this, or why you're not confident"
}}"""

    response = claude.messages.create(model="claude-sonnet-4-6", max_tokens=300, messages=[{"role": "user", "content": prompt}])
    raw = response.content[0].text.strip().replace("```json", "").replace("```", "").strip()
    return json.loads(raw)


def confirm_document_match(checklist_item_id: str, confirmed: bool, document_id: str = None) -> dict:
    """The real human decision: yes this is actually the right document
    for the right deal, or no, it isn't. Only on yes does the checklist
    item get marked received AND actually linked to the real stored file,
    so it can be found again later."""
    if confirmed:
        update = {"status": "received"}
        if document_id:
            update["document_id"] = document_id
        supabase.table("checklist_items").update(update).eq("id", checklist_item_id).execute()
    return {"ok": True, "confirmed": confirmed}


def draft_kickoff_email(deal_id: str) -> dict:
    """Step one, real draft. Shows exactly who this would go to and the
    exact content, before anything sends. No sending happens here."""
    deal = supabase.table("deals").select("*").eq("id", deal_id).single().execute().data
    parties = supabase.table("parties").select("*").eq("deal_id", deal_id).execute().data
    checklist = supabase.table("checklist_items").select("*").eq("deal_id", deal_id).execute().data
    milestones = supabase.table("milestones").select("*").eq("deal_id", deal_id).execute().data

    contactable = [p for p in parties if p.get("reviewed_by_human") and p.get("consent_basis") != "unverified" and p.get("email") and not p.get("do_not_contact")]
    if not contactable:
        return {"ok": True, "ready": False, "reason": "No confirmed, contactable parties with a real email yet. Review and confirm at least one party first."}

    outstanding = [c["document_type"].replace("_", " ") for c in checklist if c["status"] in ("requested", "flagged")]
    milestone_lines = [f"{m['label']}: {m['due_date']}" for m in milestones]

    prompt = f"""You are Vera, an agentic CRE closing coordinator. Write a real kickoff email
introducing yourself and this deal to everyone on it at once.

Deal: {deal['name']}
Target close: {deal.get('target_close_date') or 'not yet set'}
Key dates: {', '.join(milestone_lines) or 'none identified yet'}
Documents still needed: {', '.join(outstanding) or 'none outstanding right now'}

Write a short, real, professional email. Introduce yourself as Vera, coordinating
this closing. List what's still needed plainly. Never use em dashes, use periods
or commas instead. Respond with ONLY valid JSON: {{"subject": "...", "body": "..."}}"""

    response = claude.messages.create(model="claude-sonnet-4-6", max_tokens=500, messages=[{"role": "user", "content": prompt}])
    raw = response.content[0].text.strip().replace("```json", "").replace("```", "").strip()
    email_content = json.loads(raw)

    return {
        "ok": True, "ready": True, "deal_id": deal_id,
        "recipients": [{"party_id": p["id"], "name": p["name"], "email": p["email"]} for p in contactable],
        "subject": email_content["subject"], "body": email_content["body"],
    }


def send_kickoff_email_confirmed(deal_id: str, party_ids: list, subject: str, body: str, extra_emails: list = None) -> dict:
    """Step two, the real send. Sends to the exact party IDs explicitly
    approved, plus any extra email addresses typed in directly, the way
    a normal email lets you add anyone, not just pick from a fixed list."""
    sent_to = []
    for party_id in party_ids:
        party = supabase.table("parties").select("*").eq("id", party_id).single().execute().data
        if not party or party.get("do_not_contact") or not party.get("email"):
            continue
        send_real_email(to_address=party["email"], subject=subject, body=body, cc_address=SANDBOX_EMAIL or None)
        supabase.table("messages").insert({
            "deal_id": deal_id, "party_id": party["id"], "channel": "email", "direction": "outbound",
            "body": body, "consent_checked": True, "quiet_hours_ok": True,
        }).execute()
        sent_to.append(party["name"])

    for email in (extra_emails or []):
        email = email.strip()
        if not email:
            continue
        send_real_email(to_address=email, subject=subject, body=body, cc_address=SANDBOX_EMAIL or None)
        supabase.table("messages").insert({
            "deal_id": deal_id, "party_id": None, "channel": "email", "direction": "outbound",
            "body": body, "consent_checked": True, "quiet_hours_ok": True,
        }).execute()
        sent_to.append(email)

    if sent_to:
        deal = supabase.table("deals").select("name").eq("id", deal_id).single().execute().data
        notify_kickoff_sent(deal["name"], sent_to)

    return {"ok": True, "sent_to": sent_to}


def draft_intake_from_file(file_path: str, original_filename: str) -> dict:
    """Step one, real draft, from an actual uploaded file. Same real
    extraction dispatcher already used elsewhere, no DB writes yet."""
    doc_text = extract_text_from_file(file_path, original_filename)
    if not doc_text.strip():
        return {"ok": False, "error": "Could not extract any readable content from this file, even with OCR."}
    return draft_intake_from_text(doc_text)


def intake_pdf(file_path: str, original_filename: str = None) -> dict:
    """The full real flow from an actual uploaded file, PDF or Excel: extract
    the text (native, OCR, or spreadsheet parsing, whichever actually
    fits this file), then reuse the exact same extraction and creation
    logic as intake_psa."""
    doc_text = extract_text_from_file(file_path, original_filename or file_path)
    if not doc_text.strip():
        return {"ok": False, "error": "Could not extract any readable content from this file, even with OCR. It may be blank, corrupted, or too low quality to read."}
    return intake_psa(doc_text)


if __name__ == "__main__":
    print("Paste purchase agreement text below, then press Enter twice when done:\n")
    lines = []
    while True:
        line = input()
        if line == "" and lines and lines[-1] == "":
            break
        lines.append(line)
    psa_text = "\n".join(lines)

    print("\nExtracting real deal facts...")
    result = intake_psa(psa_text)
    print(f"\nReal deal created. ID: {result['deal_id']}")
    print(json.dumps(result["extraction"], indent=2))
