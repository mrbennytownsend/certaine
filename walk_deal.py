"""
Certaine — checklist and milestone walker.

This is the piece that generalizes from "reacted to one thing" to "runs the
whole file the way a real processor or closing coordinator does." It reads
a deal's ENTIRE real state from Supabase, every checklist item, every
milestone/contingency, compares it against today's date, and for each real
gap or approaching deadline, asks Vera to decide what to do.

This covers both roles in one pass, on purpose:
  - Processor-shaped work: which documents are missing or overdue.
  - Closer/TC-shaped work: which contingencies/deadlines are approaching,
    on either side of the deal.

It reads REAL rows from your live Supabase database — nothing hand-typed —
so this only works once there's real checklist_items and milestones data
for a deal. Run the seed additions below once before running this script.

RUN: python3 walk_deal.py
"""

import os
from datetime import date, datetime
from dotenv import load_dotenv
from supabase import create_client
import anthropic

load_dotenv()

supabase = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])
claude = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

DEAL_ID = "22222222-2222-2222-2222-222222222222"  # Maroa Industrial Park


def gather_full_deal_state(deal_id: str) -> dict:
    """Pull EVERYTHING about a deal — not one document pair, the whole file."""
    deal = supabase.table("deals").select("*").eq("id", deal_id).single().execute().data
    checklist = supabase.table("checklist_items").select("*").eq("deal_id", deal_id).execute().data
    milestones = supabase.table("milestones").select("*").eq("deal_id", deal_id).execute().data
    documents = supabase.table("documents").select("*").eq("deal_id", deal_id).execute().data
    parties = supabase.table("parties").select("*").eq("deal_id", deal_id).execute().data
    return {
        "deal": deal, "checklist": checklist, "milestones": milestones,
        "documents": documents, "parties": parties,
    }


def days_until(due_date_str: str) -> int:
    due = datetime.strptime(due_date_str, "%Y-%m-%d").date()
    return (due - date.today()).days


def find_real_gaps(state: dict) -> list:
    """This is the actual 'processor + closer' logic: walk every real
    checklist item and milestone, flag what's genuinely missing or close.
    No AI needed for this part, it's real, deterministic date/status math,
    the same way a real coordinator would scan a file."""
    gaps = []

    for item in state["checklist"]:
        if item["status"] in ("requested", "flagged"):
            gaps.append({
                "type": "missing_document",
                "checklist_item_id": item["id"],
                "detail": f"{item['document_type'].replace('_', ' ')} is still {item['status']}",
                "due_date": item.get("due_date"),
            })

    for m in state["milestones"]:
        if m["status"] == "pending":
            d = days_until(m["due_date"])
            if d <= 14:  # approaching soon enough to matter, mirrors the "day 10 not day 21" logic
                gaps.append({
                    "type": "approaching_milestone",
                    "milestone_id": m["id"],
                    "detail": f"{m['label']} ({m['milestone_type']}) is due in {d} days",
                    "due_date": m["due_date"],
                })

    return gaps


def decide_actions_for_gaps(state: dict, gaps: list, user_question: str = None) -> str:
    """Ask Claude to actually reason about this deal. If the user asked a
    specific question, answer THAT question directly, using the same real
    gap data as context. If no question was given, fall back to a general
    triage of what needs attention."""

    parties_summary = "\n".join(f"- {p['role']}: {p['name']}" for p in state["parties"])
    gaps_summary = "\n".join(f"- [{g['type']}] {g['detail']}" for g in gaps) or "No open gaps found."

    if user_question:
        task_instruction = f"""The broker just asked you this specific question: "{user_question}"

Answer that question directly and specifically, using the real deal data above as
context. Do not just repeat a generic triage, actually respond to what they asked."""
    else:
        task_instruction = """Give a general status update, covering whatever matters most right now."""

    prompt = f"""You are Vera, an agentic closing coordinator working the full file for this deal,
not just one document. You never price, underwrite, or approve credit.

Deal: {state['deal']['name']} ({state['deal']['deal_number']})
Target close: {state['deal']['target_close_date']}

Parties:
{parties_summary}

Here is the real, current list of open gaps across the whole file:
{gaps_summary}

{task_instruction}

Act like a real processor and closing coordinator replying to a quick check-in
from a broker over text. Here are examples of exactly the tone and length to
match:

Example 1: "Hey, heads up, both the due diligence period and closing date are
showing as already passed in the system, so I need you to confirm the actual
dates before I keep chasing docs. Everything else I'm on."

Example 2: "Still waiting on the rent roll and entity docs from the sponsor,
I've followed up twice today. Appraisal's ordered, should have it by Friday."

Example 3: "Nothing urgent right now. Survey's the only open item and it's not
due for another week."

Match that length and that tone exactly, one to two sentences, plain and
direct, the way someone genuinely texts a quick update, not a report.

You are the one who chases documents and follows up with sponsors, lenders,
title companies, and every other party. Never ask the broker to do that
chasing themselves, that is your job. Only loop the broker in directly when
something genuinely needs their decision, like a real anomaly you can't
resolve yourself.

Never use markdown formatting symbols, no pound signs, no double asterisks,
no tables, no dashes at the start of lines. Never use em dashes, use periods
or commas instead."""

    response = claude.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text


if __name__ == "__main__":
    print("Pulling the full real state of this deal from Supabase...\n")
    state = gather_full_deal_state(DEAL_ID)

    print(f"Checklist items on file: {len(state['checklist'])}")
    print(f"Milestones on file: {len(state['milestones'])}\n")

    gaps = find_real_gaps(state)
    print(f"Real gaps found: {len(gaps)}")
    for g in gaps:
        print(f"  - [{g['type']}] {g['detail']}")

    print("\nAsking Vera to triage and decide next actions...\n")
    plan = decide_actions_for_gaps(state, gaps)

    print("--- VERA'S TRIAGE ---")
    print(plan)
    print("---------------------\n")
