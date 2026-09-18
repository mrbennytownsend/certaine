"""
Certaine — local server.

This is the piece that connects the real reasoning (walk_deal.py) to the
browser demo. Without this, the demo shows pre-written text pretending to
be Vera. With this running, the demo calls a real endpoint that pulls real
data from Supabase and gets a real answer from Claude, live.

SETUP: pip3 install flask flask-cors
RUN:   python3 server.py
Leave this running in its own Terminal window/tab while you use the demo —
it needs to stay running to answer requests. Open certaine-app.html in your
browser separately, in a normal tab, while this keeps running in Terminal.
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

# Reuse everything already built and proven in walk_deal.py — no new logic,
# just exposing it over HTTP so a browser can call it.
from walk_deal import gather_full_deal_state, find_real_gaps, decide_actions_for_gaps
from take_action import run_action, draft_targeted_action, send_drafted_action
from intake import intake_psa, intake_pdf, extract_text_from_file, classify_and_match_document, confirm_document_match, draft_kickoff_email, send_kickoff_email_confirmed, store_document_file, get_document_download_url, list_deal_files, get_signed_url_for_path, draft_intake_from_text, draft_intake_from_file, confirm_intake

supabase = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])

app = Flask(__name__)
CORS(app)  # allows the browser (a different origin, file:// or localhost) to call this

MAROA_DEAL_ID = "22222222-2222-2222-2222-222222222222"


@app.route("/api/triage/<deal_id>")
def triage(deal_id):
    """Real endpoint: pulls real Supabase data for this deal, finds real
    gaps, gets a real Claude decision, returns it as JSON for the browser.
    Accepts an optional ?q= query param with the user's actual question,
    so different questions get different real answers instead of always
    returning the same fixed triage."""
    try:
        user_question = request.args.get("q")
        state = gather_full_deal_state(deal_id)
        gaps = find_real_gaps(state)
        plan = decide_actions_for_gaps(state, gaps, user_question=user_question)
        return jsonify({
            "ok": True,
            "deal_name": state["deal"]["name"],
            "gaps_found": len(gaps),
            "gaps": gaps,
            "vera_plan": plan,
        })
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/health")
def health():
    return jsonify({"status": "Vera's backend is running"})


@app.route("/api/gaps/<deal_id>")
def gaps(deal_id):
    """Real endpoint: the actual, deterministic gaps for this deal right
    now, missing documents and approaching milestones, with real IDs so
    the UI's suggestion queue can act on each one, not just describe it."""
    try:
        state = gather_full_deal_state(deal_id)
        real_gaps = find_real_gaps(state)
        return jsonify({"ok": True, "gaps": real_gaps})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/deal/<deal_id>", methods=["DELETE"])
def delete_deal(deal_id):
    """Real delete. Cascades automatically to parties, lanes, documents,
    checklist items, and messages, since the schema was built with real
    foreign key cascades from the start."""
    try:
        supabase.table("deals").delete().eq("id", deal_id).execute()
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/deals")
def list_deals():
    """Real endpoint: every deal that actually exists in Supabase, for the
    sidebar to load dynamically instead of a hardcoded list."""
    try:
        deals = supabase.table("deals").select("*").execute().data
        return jsonify({"ok": True, "deals": deals})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/deal/<deal_id>")
def deal_detail(deal_id):
    """Real endpoint: full state for one deal, milestones, parties, lanes,
    checklist, everything the UI needs to render a deal it's never seen
    hardcoded anywhere. This is what makes a brand new real deal work
    immediately, with zero code changes, the moment it's added to Supabase."""
    try:
        deal = supabase.table("deals").select("*").eq("id", deal_id).single().execute().data
        parties = supabase.table("parties").select("*").eq("deal_id", deal_id).execute().data
        lanes = supabase.table("lanes").select("*").eq("deal_id", deal_id).execute().data
        milestones = supabase.table("milestones").select("*").eq("deal_id", deal_id).order("due_date").execute().data
        checklist = supabase.table("checklist_items").select("*").eq("deal_id", deal_id).execute().data
        messages = supabase.table("messages").select("*").eq("deal_id", deal_id).order("sent_at", desc=True).execute().data
        return jsonify({
            "ok": True, "deal": deal, "parties": parties, "lanes": lanes,
            "milestones": milestones, "checklist": checklist, "messages": messages,
        })
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/act/<deal_id>", methods=["POST"])
def act(deal_id):
    """The real action endpoint. This is what makes clicking 'approve' in
    the UI actually send a real text or email, not just show fake success."""
    try:
        result = run_action(deal_id)
        return jsonify(result)
    except Exception as e:
        return jsonify({"ok": False, "sent": False, "reason": str(e)}), 500


@app.route("/api/intake", methods=["POST"])
def intake():
    """Legacy, direct-create endpoint, kept for standalone/CLI use. The
    real UI flow now uses draft-intake + confirm-intake instead, so a
    human can actually review before anything's created."""
    try:
        psa_text = request.json.get("text", "")
        if not psa_text.strip():
            return jsonify({"ok": False, "error": "No text provided."}), 400
        result = intake_psa(psa_text)
        return jsonify(result)
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/draft-intake", methods=["POST"])
def draft_intake_route():
    """Real draft, from pasted text. Extracts everything, writes nothing
    yet, this is the actual real flow the UI uses now."""
    try:
        psa_text = request.json.get("text", "")
        if not psa_text.strip():
            return jsonify({"ok": False, "error": "No text provided."}), 400
        result = draft_intake_from_text(psa_text)
        return jsonify(result)
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/draft-intake-pdf", methods=["POST"])
def draft_intake_pdf_route():
    """Real draft, from an actual uploaded file, PDF or Excel."""
    try:
        if "file" not in request.files:
            return jsonify({"ok": False, "error": "No file uploaded."}), 400
        uploaded = request.files["file"]
        temp_path = os.path.join("/tmp", uploaded.filename)
        uploaded.save(temp_path)
        result = draft_intake_from_file(temp_path, uploaded.filename)
        os.remove(temp_path)
        return jsonify(result)
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/confirm-intake", methods=["POST"])
def confirm_intake_route():
    """The real creation, only after a human has seen the draft, edited
    anything wrong, and explicitly confirmed."""
    try:
        extraction = request.json.get("extraction")
        if not extraction:
            return jsonify({"ok": False, "error": "No extraction data provided."}), 400
        result = confirm_intake(extraction)
        return jsonify(result)
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/intake-pdf", methods=["POST"])
def intake_pdf_route():
    """The real intake endpoint, from an actual uploaded PDF file."""
    try:
        if "file" not in request.files:
            return jsonify({"ok": False, "error": "No file uploaded."}), 400
        uploaded = request.files["file"]
        temp_path = os.path.join("/tmp", uploaded.filename)
        uploaded.save(temp_path)
        result = intake_pdf(temp_path, uploaded.filename)
        os.remove(temp_path)
        return jsonify(result)
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/draft-action/<checklist_item_id>", methods=["POST"])
def draft_action(checklist_item_id):
    """Real draft, no sending yet. Returns the actual message so a human
    can see exactly what would go out before approving it."""
    try:
        result = draft_targeted_action(checklist_item_id)
        return jsonify(result)
    except Exception as e:
        return jsonify({"ok": False, "ready": False, "reason": str(e)}), 500


@app.route("/api/send-action", methods=["POST"])
def send_action():
    """The real send, only after a human has seen and approved the draft."""
    try:
        body = request.json or {}
        result = send_drafted_action(
            body["checklist_item_id"], body["party_id"], body["channel"], body["message"], body["deal_id"],
        )
        return jsonify(result)
    except Exception as e:
        return jsonify({"ok": False, "sent": False, "reason": str(e)}), 500


@app.route("/api/deal/<deal_id>/notes", methods=["POST"])
def save_notes(deal_id):
    """Real, simple freeform notes, saved directly."""
    try:
        body = request.json or {}
        supabase.table("deals").update({"notes": body.get("notes", "")}).eq("id", deal_id).execute()
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/upload-for-item/<checklist_item_id>", methods=["POST"])
def upload_for_item(checklist_item_id):
    """Scoped upload: you already know which document this is, so skip
    classification entirely, actually store the real file permanently,
    and mark it received directly."""
    try:
        if "file" not in request.files:
            return jsonify({"ok": False, "error": "No file uploaded."}), 400
        item = supabase.table("checklist_items").select("*").eq("id", checklist_item_id).single().execute().data
        uploaded = request.files["file"]
        temp_path = os.path.join("/tmp", uploaded.filename)
        uploaded.save(temp_path)
        document_id = store_document_file(item["deal_id"], item["document_type"], checklist_item_id, temp_path, uploaded.filename)
        os.remove(temp_path)
        supabase.table("checklist_items").update({"status": "received", "document_id": document_id}).eq("id", checklist_item_id).execute()
        return jsonify({"ok": True, "document_id": document_id})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/deal/<deal_id>/party", methods=["POST"])
def add_party(deal_id):
    """Manually add a party, for when extraction missed someone or
    there's no document to extract from at all."""
    try:
        body = request.json or {}
        result = supabase.table("parties").insert({
            "deal_id": deal_id, "role": body.get("role", "other"), "name": body.get("name", ""),
            "org_name": body.get("org_name"), "email": body.get("email"), "phone": body.get("phone"),
            "consent_basis": "unverified", "reviewed_by_human": False,
        }).execute()
        return jsonify({"ok": True, "party_id": result.data[0]["id"]})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/party/<party_id>/confirm", methods=["POST"])
def confirm_party(party_id):
    """The real gate: a human reviews and corrects an extracted party's
    real contact info, then confirms it. Only after this can Vera ever
    actually contact them, this is what check_guardrails checks for."""
    try:
        body = request.json or {}
        update = {"reviewed_by_human": True}
        if "email" in body:
            update["email"] = body["email"]
        if "phone" in body:
            update["phone"] = body["phone"]
        if "name" in body:
            update["name"] = body["name"]
        if body.get("consent_confirmed"):
            update["consent_basis"] = "informational_transactional"
        supabase.table("parties").update(update).eq("id", party_id).execute()
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/kickoff-email/<deal_id>", methods=["POST"])
def kickoff_email(deal_id):
    """Real draft, shows exactly who this would go to before anything sends."""
    try:
        result = draft_kickoff_email(deal_id)
        return jsonify(result)
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/send-kickoff-email", methods=["POST"])
def send_kickoff_email_route():
    """The real send, only after a human has seen the exact recipient
    list and content and explicitly approved it."""
    try:
        body = request.json or {}
        result = send_kickoff_email_confirmed(body["deal_id"], body["party_ids"], body["subject"], body["body"], body.get("extra_emails"))
        return jsonify(result)
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/upload-document/<deal_id>", methods=["POST"])
def upload_document(deal_id):
    """Real upload, real classification, real matching against THIS
    deal's actual checklist, and real permanent storage. Does not link
    the file to a checklist item yet, that only happens after a human
    confirms via /api/confirm-document, but the file itself is kept
    either way, not thrown away on a rejected match."""
    try:
        if "file" not in request.files:
            return jsonify({"ok": False, "error": "No file uploaded."}), 400
        uploaded = request.files["file"]
        temp_path = os.path.join("/tmp", uploaded.filename)
        uploaded.save(temp_path)
        doc_text = extract_text_from_file(temp_path, uploaded.filename)
        if not doc_text.strip():
            os.remove(temp_path)
            return jsonify({"ok": False, "error": "Could not extract any readable text, even with OCR."}), 400
        result = classify_and_match_document(deal_id, doc_text)
        document_id = store_document_file(deal_id, result["document_type"], None, temp_path, uploaded.filename)
        os.remove(temp_path)
        result["document_id"] = document_id
        return jsonify({"ok": True, "classification": result})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/document-url/<document_id>")
def document_url(document_id):
    """Real, temporary signed URL to actually view or download a stored
    file, not a permanent public link, since these are real, sensitive
    deal documents."""
    try:
        url = get_document_download_url(document_id)
        if not url:
            return jsonify({"ok": False, "error": "No file found."}), 404
        return jsonify({"ok": True, "url": url})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/deal/<deal_id>/files")
def deal_files(deal_id):
    """The real file browser: everything actually stored for this deal,
    not filtered through checklist items, the actual answer to
    'where are my files.'"""
    try:
        files = list_deal_files(deal_id)
        return jsonify({"ok": True, "files": files})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/file-url", methods=["POST"])
def file_url():
    """Real signed URL for a specific file in the browser, by its path."""
    try:
        body = request.json or {}
        url = get_signed_url_for_path(body["path"])
        return jsonify({"ok": True, "url": url})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/confirm-document", methods=["POST"])
def confirm_document():
    """The real human decision on whether a proposed document match is
    actually correct, only this actually updates the checklist."""
    try:
        body = request.json or {}
        result = confirm_document_match(body.get("checklist_item_id"), body.get("confirmed", False), body.get("document_id"))
        return jsonify(result)
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


if __name__ == "__main__":
    print("Starting Certaine's local server...")
    print("Health check: http://localhost:5001/api/health")
    print(f"Real triage:  http://localhost:5001/api/triage/{MAROA_DEAL_ID}")
    print("\nLeave this running. Open certaine-app.html separately in your browser.\n")
    app.run(port=5001, debug=True)
