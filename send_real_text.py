"""
Certaine — real Twilio SMS sending.

This is the first genuinely real communication channel. Everything before
this point (Slack windows, iMessage mockups, email clients in the HTML)
was display data. This actually sends a real text message through your
real Twilio account to a real phone number.

SETUP:
  1. pip3 install twilio
  2. Add three more lines to your .env file:
       TWILIO_ACCOUNT_SID=your-account-sid
       TWILIO_AUTH_TOKEN=your-auth-token
       TWILIO_PHONE_NUMBER=+1XXXXXXXXXX   (the real Twilio number you own)

     Find these in your Twilio Console (console.twilio.com), right on the
     dashboard homepage: Account SID and Auth Token are both shown there.
     Your Twilio phone number is under Phone Numbers > Manage > Active Numbers.

  3. Run: python3 send_real_text.py

WHAT THIS DOES NOT DO YET, being honest about the real gap:
  - This sends ONE test text to a number you specify. It is not yet wired
    into orchestrate.py or walk_deal.py, so Vera's actual decisions don't
    trigger this automatically yet. That wiring is the next real step,
    once this base send function is confirmed working.
  - Receiving REPLIES requires Twilio to call a webhook URL on YOUR
    machine, which localhost cannot do by default. That needs a tunneling
    tool like ngrok to expose your local server publicly. Not built yet,
    flagged here so it's a known next step, not a surprise later.
"""

import os
from dotenv import load_dotenv
from twilio.rest import Client

load_dotenv()

TWILIO_SID = os.environ["TWILIO_ACCOUNT_SID"]
TWILIO_TOKEN = os.environ["TWILIO_AUTH_TOKEN"]
TWILIO_FROM = os.environ["TWILIO_PHONE_NUMBER"]

client = Client(TWILIO_SID, TWILIO_TOKEN)


def send_real_text(to_number: str, body: str):
    """Sends a REAL text message. This is not a simulation.
    to_number must be in E.164 format, e.g. +19495551234"""
    message = client.messages.create(
        body=body,
        from_=TWILIO_FROM,
        to=to_number,
    )
    return message.sid  # Twilio's confirmation ID for this real message


if __name__ == "__main__":
    print("This will send a REAL text message through your real Twilio number.")
    test_number = input("Enter a real phone number to test with (E.164 format, e.g. +19495551234): ").strip()
    test_body = "This is a real test message from Certaine's Vera backend. If you got this, the Twilio connection actually works."

    print(f"\nSending to {test_number}...")
    sid = send_real_text(test_number, test_body)
    print(f"Sent. Twilio message SID: {sid}")
    print("Check that phone, it should have a real text within a few seconds.")
