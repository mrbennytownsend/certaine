"""
Certaine — real internal Slack notifications.

This is the missing half of communication: everything else Vera does
talks to the outside world (sponsors, lenders, title companies). This
posts real updates to your own team's Slack, so you know what she's
doing without having to open the app and check.

SETUP:
  1. In Slack, go to api.slack.com/apps, create an app (or use an existing
     one), enable "Incoming Webhooks", and add a webhook to the channel
     you want updates posted to. Slack gives you a URL like:
  2. Add one line to your .env file:

If this isn't set, every call here quietly does nothing, real graceful
degradation, not an error, since Slack is optional, not required for the
rest of the app to work.

WHAT THIS DOES NOT DO YET, honestly: this only posts outward. It doesn't
read replies or respond to anything typed in Slack, that's real inbound
work, same category as the inbound email/text gap already named.
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL", "")


def post_to_slack(text: str) -> bool:
    """Posts a real message to your real Slack channel. Returns False,
    silently, if no webhook is configured, rather than erroring out."""
    if not SLACK_WEBHOOK_URL:
        return False
    try:
        requests.post(SLACK_WEBHOOK_URL, json={"text": text}, timeout=5)
        return True
    except Exception:
        return False


def notify_action_sent(deal_name: str, channel: str, party_name: str, message: str):
    """The real internal update after Vera actually sends something."""
    post_to_slack(
        f"*Vera* just sent a real {channel} to *{party_name}* on *{deal_name}*:\n> {message}"
    )


def notify_kickoff_sent(deal_name: str, sent_to: list):
    """The real internal update after a kickoff email actually goes out."""
    names = ", ".join(sent_to) if sent_to else "nobody, check contact info"
    post_to_slack(f"*Vera* sent the kickoff email for *{deal_name}* to: {names}")
