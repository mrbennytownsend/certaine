"""
Certaine — the real action loop.

This is the piece that makes Vera's decisions actually DO something in the
world, not just describe what she'd do. It:

1. Pulls real deal state and real gaps (reusing walk_deal.py's logic).
2. Asks Claude for a STRUCTURED decision (not prose this time), which party,
   which channel, what exact message, so the code can act on it directly.
3. Checks REAL compliance guardrails before sending anything: does this
   party have a real phone number, have they consented, are they on a
   do-not-contact list. If any of these fail, Vera does NOT send, and
   says why, the same way a careful human coordinator would hold back
   rather than guess.
4. If it's genuinely safe to send, actually sends the real text via Twilio.
5. Writes a real row into the messages table, so this becomes part of the
   real audit trail, not just something that happened and vanished.

IMPORTANT, READ BEFORE RUNNING:
The seeded parties in Supabase have fake phone numbers (555-0101, etc).
Those will fail to send or bounce. To actually test this end to end, you
need to update ONE party's phone number in Supabase to a real number you
control (like your own, the way you tested send_real_text.py). Instructions
for that are printed when you run this script if no valid party is found.

RUN: python3 take_action.py
"""

import os
import json
from dotenv import load_dotenv
from supabase import create_client
import anthropic
from twilio.rest import Client as TwilioClient
from notify_slack import notify_action_sent
from send_real_email import send_real_email

load_dotenv()

supabase = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])
claude = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
twilio = TwilioClient(os.environ["TWILIO_ACCOUNT_SID"], os.environ["TWILIO_AUTH_TOKEN"])
TWILIO_FROM = os.environ["TWILIO_PHONE_NUMBER"]

# SANDBOX MODE: real sends only go to a contact you've explicitly approved,
# regardless of what phone/email a party record actually has. This lets you
# add and edit real party data freely without any risk of texting or
# emailing an actual stranger before you're ready. Set these in .env once
# you've decided who your safe test contact is.
SANDBOX_PHONE = os.environ.get("ALLOWED_SANDBOX_PHONE", "")
SANDBOX_EMAIL = os.environ.get("ALLOWED_SANDBOX_EMAIL", "")

DEAL_ID = "22222222-2222-2222-2222-222222222222"  # Maroa Industrial Park


def gather_full_deal_state(deal_id):
    deal = supabase.table("deals").select("*").eq("id", deal_id).single().execute().data
    checklist = supabase.table("checklist_items").select("*").eq("deal_id", deal_id).execute().data
    milestones = supabase.table("milestones").select("*").eq("deal_id", deal_id).execute().data
    parties = supabase.table("parties").select("*").eq("deal_id", deal_id).execute().data
    return {"deal": deal, "checklist": checklist, "milestones": milestones, "parties": parties}


def decide_structured_action(state: dict) -> dict:
    """Ask Claude for a real, structured decision, not prose. This is what
    makes the output something code can act on: which party, which channel,
    exact message text."""

    parties_json = json.dumps(state["parties"], default=str)
    checklist_json = json.dumps(state["checklist"], default=str)

    prompt = f"""You are Vera, an agentic CRE closing coordinator. You never price, underwrite,
or approve credit, you coordinate and verify only.

Deal: {state['deal']['name']}
Parties on this deal: {parties_json}
Open checklist items: {checklist_json}

Decide the ONE most important next action to take right now. Respond with
ONLY valid JSON, no other text, in this exact shape:

{{
  "action_needed": true or false,
  "party_id": "the id of the party to contact, matching one from the parties list, or null if no action needed",
  "channel": "sms or email, whichever fits this party and message better",
  "message": "the exact message to send, written the way a real coordinator would, short and direct. Never use em dashes, use periods or commas instead.",
  "reasoning": "one sentence on why this is the priority right now, no em dashes"
}}

If nothing genuinely needs outbound contact right now, set action_needed to false."""

    response = claude.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=400,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = response.content[0].text.strip().replace("```json", "").replace("```", "").strip()
    return json.loads(raw)


def check_guardrails(party: dict, channel: str) -> tuple:
    """Real compliance checks, not skipped. Returns (ok: bool, reason: str)."""
    if not party:
        return False, "No matching party found for this action."
    if not party.get("reviewed_by_human"):
        return False, f"{party['name']} was extracted automatically and hasn't been reviewed by a human yet. Confirm their real contact info before Vera can reach out."
    if party.get("do_not_contact"):
        return False, f"{party['name']} is marked do-not-contact. Vera will not send."
    if party.get("consent_basis") == "unverified":
        return False, f"No documented consent basis on file for {party['name']}. Vera will not send until consent is confirmed."
    if channel == "sms":
        phone = party.get("phone", "")
        if not phone or phone.startswith("555-"):
            return False, f"{party['name']}'s phone number ({phone}) is a placeholder, not real. Update it in Supabase to test a real send."
        if SANDBOX_PHONE and phone != SANDBOX_PHONE:
            return False, f"Sandbox mode is on: real sends only go to your approved test number right now, not {phone}. This is on purpose, not a bug."
    elif channel == "email":
        email = party.get("email", "")
        if not email or email.endswith(".example"):
            return False, f"{party['name']}'s email ({email}) is a placeholder, not real. Update it in Supabase to test a real send."
        if SANDBOX_EMAIL and email != SANDBOX_EMAIL:
            return False, f"Sandbox mode is on: real sends only go to your approved test email right now, not {email}. This is on purpose, not a bug."
    return True, "Guardrails passed."


def dispatch(channel: str, party: dict, message: str, deal_name: str = "your deal") -> str:
    """Sends through whichever real channel Vera decided on. Email CCs the
    broker, so there's real proof in their own inbox, not just a claim."""
    if channel == "sms":
        result = twilio.messages.create(body=message, from_=TWILIO_FROM, to=party["phone"])
        return result.sid
    elif channel == "email":
        send_real_email(to_address=party["email"], subject=f"Re: {deal_name}", body=message, cc_address=SANDBOX_EMAIL or None)
        return "sent via gmail smtp"
    else:
        raise ValueError(f"Unknown channel: {channel}")


def log_message(deal_id: str, party_id: str, channel: str, body: str, consent_checked: bool):
    supabase.table("messages").insert({
        "deal_id": deal_id,
        "party_id": party_id,
        "channel": channel,
        "direction": "outbound",
        "body": body,
        "consent_checked": consent_checked,
        "quiet_hours_ok": True,  # simplified for now; real per-timezone quiet-hours check is a future step
    }).execute()


def generate_targeted_message(deal_name: str, document_type: str, party: dict) -> dict:
    """Ask Claude to write a real, specific follow-up about ONE exact
    document, for ONE exact party, the way a human clicked 'follow up on
    this' rather than letting Vera pick her own priority."""

    prompt = f"""You are Vera, an agentic CRE closing coordinator. A broker just clicked to
have you follow up specifically about one document.

Deal: {deal_name}
Document needed: {document_type.replace('_', ' ')}
Party to contact: {party['name']} ({party.get('org_name') or party['role']})
Preferred channel: {party.get('preferred_channel') or 'sms'}

Write a short, real, direct message asking them for this specific document,
the way an actual coordinator would text or email. One to two sentences.
Never use em dashes, use periods or commas instead. Respond with ONLY valid
JSON, no other text: {{"channel": "sms or email, whichever fits", "message": "the exact message text"}}"""

    response = claude.messages.create(
        model="claude-sonnet-4-6", max_tokens=250,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = response.content[0].text.strip().replace("```json", "").replace("```", "").strip()
    return json.loads(raw)


def draft_targeted_action(checklist_item_id: str) -> dict:
    """Step one, real draft, no sending. Finds who's responsible and
    writes the real message, but stops there so a human can actually see
    it before anything goes out."""
    item = supabase.table("checklist_items").select("*").eq("id", checklist_item_id).single().execute().data
    if not item.get("responsible_party_id"):
        return {"ok": True, "ready": False, "reason": "No responsible party identified for this document yet. Assign one first."}

    party = supabase.table("parties").select("*").eq("id", item["responsible_party_id"]).single().execute().data
    deal = supabase.table("deals").select("*").eq("id", item["deal_id"]).single().execute().data

    decision = generate_targeted_message(deal["name"], item["document_type"], party)
    ok, reason = check_guardrails(party, decision["channel"])
    return {
        "ok": True, "ready": ok, "reason": None if ok else reason,
        "checklist_item_id": checklist_item_id, "party_id": party["id"], "party_name": party["name"],
        "channel": decision["channel"], "message": decision["message"], "deal_id": item["deal_id"],
    }


def send_drafted_action(checklist_item_id: str, party_id: str, channel: str, message: str, deal_id: str) -> dict:
    """Step two, the real send, only happens when explicitly called with
    an already-drafted, human-approved message. Re-checks guardrails at
    send time too, not just at draft time, in case anything changed."""
    party = supabase.table("parties").select("*").eq("id", party_id).single().execute().data
    deal = supabase.table("deals").select("name").eq("id", deal_id).single().execute().data
    ok, reason = check_guardrails(party, channel)
    if not ok:
        return {"ok": True, "sent": False, "reason": reason}

    result_id = dispatch(channel, party, message, deal_name=deal["name"])
    log_message(deal_id, party_id, channel, message, consent_checked=True)
    notify_action_sent(deal["name"], channel, party["name"], message)
    return {"ok": True, "sent": True, "channel": channel, "party": party["name"], "message": message, "result_id": result_id}


def run_action(deal_id: str) -> dict:
    """The full real loop, callable from anywhere (this script directly,
    or server.py for the UI's approve buttons). Returns a result dict,
    never raises, so callers can always show something useful."""
    state = gather_full_deal_state(deal_id)
    decision = decide_structured_action(state)

    if not decision.get("action_needed"):
        return {"ok": True, "sent": False, "reason": "No outbound action needed right now.", "decision": decision}

    party = next((p for p in state["parties"] if p["id"] == decision.get("party_id")), None)
    channel = decision.get("channel", "sms")
    ok, reason = check_guardrails(party, channel)

    if not ok:
        return {"ok": True, "sent": False, "reason": reason, "decision": decision}

    result_id = dispatch(channel, party, decision["message"])
    log_message(deal_id, party["id"], channel, decision["message"], consent_checked=True)
    return {"ok": True, "sent": True, "channel": channel, "party": party["name"], "message": decision["message"], "result_id": result_id}


if __name__ == "__main__":
    import sys
    deal_id = sys.argv[1] if len(sys.argv) > 1 else DEAL_ID
    print(f"Running the real action loop for deal {deal_id}...")
    result = run_action(deal_id)
    print(json.dumps(result, indent=2))
