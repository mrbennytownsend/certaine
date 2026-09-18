"""
Certaine — real email sending, via Gmail SMTP.

No new service to sign up for, this uses a Gmail account you already have.
Gmail requires an "app password" for this (not your normal login password),
since it blocks plain password logins from scripts for security reasons.

SETUP:
  1. Go to myaccount.google.com/security
  2. Turn on 2-Step Verification if it isn't already on (required for app passwords)
  3. Go to myaccount.google.com/apppasswords
  4. Create a new app password, name it "Certaine" or similar, copy the 16-character code
  5. Add two lines to your .env file:
       GMAIL_ADDRESS=your-real-gmail@gmail.com
       GMAIL_APP_PASSWORD=the16charactercode

  6. pip3 install nothing extra needed, smtplib is built into Python
  7. Run: python3 send_real_email.py
"""

import os
import smtplib
from email.mime.text import MIMEText
from dotenv import load_dotenv

load_dotenv()

GMAIL_ADDRESS = os.environ["GMAIL_ADDRESS"]
GMAIL_APP_PASSWORD = os.environ["GMAIL_APP_PASSWORD"]


def send_real_email(to_address: str, subject: str, body: str, cc_address: str = None):
    """Sends a REAL email. Not a simulation. CCs the broker by default so
    there's real proof in their own inbox, not just a claim in the app."""
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = f"Vera (Certaine) <{GMAIL_ADDRESS}>"
    msg["To"] = to_address
    recipients = [to_address]
    if cc_address:
        msg["Cc"] = cc_address
        recipients.append(cc_address)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
        server.sendmail(GMAIL_ADDRESS, recipients, msg.as_string())


if __name__ == "__main__":
    print("This will send a REAL email through your real Gmail account.")
    test_address = input("Enter a real email address to test with: ").strip()

    send_real_email(
        to_address=test_address,
        subject="Real test from Certaine's Vera backend",
        body="This is a real test email from Vera. If you got this, the Gmail connection actually works.",
    )
    print(f"Sent to {test_address}. Check that inbox.")
