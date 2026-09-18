"""
Certaine — document extraction and reconciliation.

This is the piece that makes "she reads the documents, not just a checklist"
literally true instead of a claim. It takes real text (from a rent roll or a
T-12, pasted in or pulled from a PDF) and:

1. Asks Claude to extract structured fields from it (occupancy, unit count,
   NOI, etc.) — this is real extraction, not a hardcoded number.
2. Runs the same extraction on a second document.
3. Reconciles the two and reports back whether they actually agree, and if
   not, by how much and why that might be.

WHY USE CLAUDE FOR EXTRACTION INSTEAD OF CUSTOM OCR/REGEX:
Rent rolls and T-12s aren't standardized (this is called out directly in the
original product spec) — every lender and property manager formats them
differently. A general-purpose language model reading the raw text and
extracting fields by understanding what a "rent roll" or "T-12" IS, rather
than matching a fixed template, is genuinely the practical approach here.

WHAT THIS DOESN'T DO YET (be honest about the gap):
It takes TEXT as input. Real documents usually arrive as PDFs, sometimes
scanned images. Getting from "a PDF file" to "clean text" is a separate,
real step (a library like pdfplumber handles native-text PDFs; scanned PDFs
need OCR, e.g. via pytesseract). That conversion step is NOT built yet —
this script assumes you already have text. Wiring up PDF-to-text is the
next honest task after this one works well on pasted text.

SETUP: same .env file as orchestrate.py, reuses ANTHROPIC_API_KEY.
RUN: python3 extract_and_reconcile.py
"""

import os
import json
from dotenv import load_dotenv
import anthropic

load_dotenv()
claude = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])


def extract_fields(document_text: str, document_type: str) -> dict:
    """Ask Claude to pull structured fields out of raw document text.
    Returns a real dict, not a hardcoded example."""

    prompt = f"""You are extracting structured data from a commercial real estate {document_type}.

Here is the raw document text:
---
{document_text}
---

Extract the following as JSON only, no other text, no markdown formatting:
- occupancy_pct (number, the occupancy percentage if stated or calculable)
- total_units (number, if applicable)
- occupied_units (number, if applicable)
- noi_annual (number, annual net operating income if this is a T-12, otherwise null)
- gross_rent_annual (number, if calculable, otherwise null)
- as_of_date (string, the date this document reflects, if stated, otherwise null)
- notes (string, anything unusual you noticed, e.g. "one unit shows a move-out mid-period")

Return ONLY valid JSON, nothing else."""

    response = claude.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = response.content[0].text.strip()
    # Claude sometimes wraps JSON in code fences even when told not to — strip them defensively
    raw = raw.replace("```json", "").replace("```", "").strip()
    return json.loads(raw)


def reconcile(rent_roll_data: dict, t12_data: dict) -> dict:
    """Ask Claude to actually reason about whether these two extracted
    documents agree, the same judgment call a real coordinator makes,
    not just a numeric diff."""

    prompt = f"""You are Vera, a CRE closing coordinator. You've extracted data from two documents
on the same deal and need to check whether they reconcile.

Rent roll data: {json.dumps(rent_roll_data)}
T-12 data: {json.dumps(t12_data)}

Do these two documents agree with each other on occupancy? If there's a
discrepancy, state the exact percentage gap, and give your real professional
judgment on the most likely explanation (e.g. a unit turned mid-period, one
document is stale, a data entry issue). Then say plainly whether this is
something to flag to the lender proactively or a normal, explainable variance.

Respond in 3-4 sentences, the way you'd actually explain it to a broker."""

    response = claude.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=300,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text


# ============================================================
# Realistic sample documents to test against right now, before
# you have a real PDF to feed in. Replace these strings with real
# rent roll / T-12 text (pasted from an actual PDF) to test for real.
# ============================================================

SAMPLE_RENT_ROLL = """
RENT ROLL - Maroa Industrial Park
As of: July 15, 2025

Unit 101 - Occupied - Tenant: ACME Logistics - Rent: $12,400/mo
Unit 102 - Occupied - Tenant: Pinnacle Freight - Rent: $9,800/mo
Unit 103 - Vacant (turned July 1, 2025, previously Coastal Storage)
Unit 104 - Occupied - Tenant: Summit Warehousing - Rent: $11,200/mo
Unit 105 - Occupied - Tenant: Delta Distribution - Rent: $10,600/mo

Total Units: 5
Occupied: 4
Occupancy: 80%
"""

SAMPLE_T12 = """
T-12 OPERATING STATEMENT - Maroa Industrial Park
Period: July 2024 - June 2025

Gross Potential Rent: $658,800
Vacancy Loss: $32,940
Effective Gross Income: $625,860
Operating Expenses: $187,758
Net Operating Income: $438,102

Note: Occupancy averaged 94% across the trailing 12-month period.
"""

if __name__ == "__main__":
    print("Extracting rent roll fields...")
    rent_roll_data = extract_fields(SAMPLE_RENT_ROLL, "rent roll")
    print(json.dumps(rent_roll_data, indent=2))

    print("\nExtracting T-12 fields...")
    t12_data = extract_fields(SAMPLE_T12, "T-12 operating statement")
    print(json.dumps(t12_data, indent=2))

    print("\n--- VERA'S RECONCILIATION ---")
    result = reconcile(rent_roll_data, t12_data)
    print(result)
    print("------------------------------\n")
