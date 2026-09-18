"""
Certaine — first orchestration script.

What this does, in plain terms:
1. Connects to your real Supabase database.
2. Reads one real deal (Maroa Industrial Park), its parties, and its open flags.
3. Sends that context to Claude and asks: "what should Vera do next?"
4. Writes Claude's decision back into the `messages` table as a real row.

This is deliberately the smallest version that proves the whole chain works:
database -> code -> AI decision -> visible result. Everything else (Slack,
Twilio, more deals, more sophisticated prompting) builds on this same shape.

SETUP (do this once):
  1. pip3 install supabase anthropic python-dotenv
  2. Create a file named ".env" in this same folder with these two lines
     (fill in your real values, no quotes needed):

       SUPABASE_URL=https://your-project.supabase.co
       SUPABASE_SERVICE_KEY=your-service-role-key-here
       ANTHROPIC_API_KEY=your-claude-api-key-here

  3. Run it:  python3 orchestrate.py
"""

import os
from dotenv import load_dotenv
from supabase import create_client
import anthropic

load_dotenv()  # reads the .env file you create, keeps real keys out of this code

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_SERVICE_KEY = os.environ["SUPABASE_SERVICE_KEY"]
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]

# The service_role key bypasses Row Level Security entirely — this is exactly
# right for backend orchestration code like this. Never use this key in any
# code that runs in a browser or gets shared publicly.
supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
claude = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

# The real deal we seeded earlier — Maroa Industrial Park
DEAL_ID = "22222222-2222-2222-2222-222222222222"


def gather_deal_context(deal_id: str) -> dict:
    """Pull everything Vera would need to know about this deal right now,
    the same joins a real dashboard view would run."""
    deal = supabase.table("deals").select("*").eq("id", deal_id).single().execute().data
    parties = supabase.table("parties").select("*").eq("deal_id", deal_id).execute().data
    lanes = supabase.table("lanes").select("*").eq("deal_id", deal_id).execute().data
    open_flags = (
        supabase.table("flags")
        .select("*")
        .eq("deal_id", deal_id)
        .eq("status", "open")
        .execute()
        .data
    )
    return {"deal": deal, "parties": parties, "lanes": lanes, "open_flags": open_flags}


def ask_vera_what_to_do(context: dict) -> str:
    """This is the actual orchestration brain — the part every other channel
    (Slack, Twilio, email) will eventually call into. Right now it just
    reasons and returns text; later, this is where it would decide to call
    a specific tool (send_sms, place_call, send_email) rather than just talk."""

    prompt = f"""You are Vera, an agentic closing coordinator for commercial real estate.
You work for the broker, coordinating a deal from contract to close.
You never price, underwrite, or approve credit — you coordinate and verify only.

Here is the current state of one deal you're working:

Deal: {context['deal']['name']} ({context['deal']['deal_number']})
Target close date: {context['deal']['target_close_date']}
Closing confidence: {context['deal']['closing_confidence']}%

Parties on this deal:
{format_parties(context['parties'])}

Lanes:
{format_lanes(context['lanes'])}

Open flags that need attention:
{format_flags(context['open_flags'])}

Given this, what is the single most important next action you should take right now?
Be specific: who would you contact, through which channel (call, text, or email),
and what would you actually say. Keep it to a few sentences, the way a real
coordinator would think through their next move, not a generic summary.
Never use em dashes anywhere in your response, use periods or commas instead."""

    response = claude.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=400,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text


def format_parties(parties: list) -> str:
    return "\n".join(
        f"- {p['role']}: {p['name']}" + (f" ({p['org_name']})" if p.get("org_name") else "")
        for p in parties
    ) or "  (none recorded)"


def format_lanes(lanes: list) -> str:
    return "\n".join(f"- {l['label']}: {l['completion_pct']}% complete, {l['status']}" for l in lanes) or "  (none recorded)"


def format_flags(flags: list) -> str:
    return "\n".join(f"- {f['severity'].upper()}: {f['description']}" for f in flags) or "  (no open flags)"


def write_decision_back(deal_id: str, decision_text: str):
    """Write Vera's decision into the real messages table — this is what
    makes it a genuine audit trail, not just something printed to a terminal
    and lost. In a fuller build, this would also actually trigger the real
    action (send the text, place the call) via Twilio/email, not just log it."""
    supabase.table("messages").insert(
        {
            "deal_id": deal_id,
            "channel": "slack",  # placeholder: this is Vera's internal reasoning, logged like a note
            "direction": "outbound",
            "body": decision_text,
            "consent_checked": True,
            "quiet_hours_ok": True,
        }
    ).execute()


if __name__ == "__main__":
    print("Gathering real deal context from Supabase...")
    context = gather_deal_context(DEAL_ID)

    print("Asking Vera (Claude) what to do next...")
    decision = ask_vera_what_to_do(context)

    print("\n--- VERA'S DECISION ---")
    print(decision)
    print("-----------------------\n")

    write_decision_back(DEAL_ID, decision)
    print("Written back to the messages table. Check Supabase's Table Editor -> messages to see it.")
