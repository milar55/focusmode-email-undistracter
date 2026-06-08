#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["requests"]
# ///
"""Focus-mode inbox tooling.

Two subcommands:
  sweep  - Move matching inbox mail from the last 2 hours (forums tab +
           List-Unsubscribe newsletters) out of the inbox and into the
           `Focus-Muted` label. Label-only; emails are NEVER deleted.
  nudge  - Send a midday check-in email to self.
  reverse - Restore all messages with `Focus-Muted` label back to the Inbox.
"""
import base64
import os
import sys
from email.mime.text import MIMEText

import requests

ACCOUNT_ID = "e49b4b07-e6fc-4ec2-9dbc-f8385f577480"
USER_EMAIL = "rudmilarahman@gmail.com"
LABEL_NAME = "Focus-Muted"
SWEEP_QUERY = "in:inbox newer_than:2h (category:forums OR list:*)"

PROXY = os.environ["PROXY_BASE_URL"].rstrip("/")
TOKEN = os.environ["PROXY_TOKEN"]
BASE = f"{PROXY}/{ACCOUNT_ID}/gmail.googleapis.com/gmail/v1/users/me"
HEADERS = {"Authorization": f"Bearer {TOKEN}"}


def get_or_create_label():
    r = requests.get(f"{BASE}/labels", headers=HEADERS, timeout=30)
    r.raise_for_status()
    for lbl in r.json().get("labels", []):
        if lbl["name"] == LABEL_NAME:
            return lbl["id"]
    r = requests.post(
        f"{BASE}/labels",
        headers=HEADERS,
        json={"name": LABEL_NAME, "labelListVisibility": "labelShow", "messageListVisibility": "show"},
        timeout=30,
    )
    r.raise_for_status()
    return r.json()["id"]


def sweep():
    label_id = get_or_create_label()
    ids = []
    page_token = None
    while True:
        params = {"q": SWEEP_QUERY, "maxResults": 100}
        if page_token:
            params["pageToken"] = page_token
        r = requests.get(f"{BASE}/messages", headers=HEADERS, params=params, timeout=30)
        r.raise_for_status()
        data = r.json()
        ids.extend(m["id"] for m in data.get("messages", []))
        page_token = data.get("nextPageToken")
        if not page_token:
            break
    if not ids:
        print("Nothing to sweep.")
        return
    # batchModify accepts up to 1000 ids per call. Label-only - no delete.
    for i in range(0, len(ids), 1000):
        chunk = ids[i : i + 1000]
        r = requests.post(
            f"{BASE}/messages/batchModify",
            headers=HEADERS,
            json={"ids": chunk, "removeLabelIds": ["INBOX"], "addLabelIds": [label_id]},
            timeout=60,
        )
        r.raise_for_status()
    print(f"Swept {len(ids)} message(s) out of inbox into '{LABEL_NAME}'.")


def nudge():
    msg = MIMEText(
        "Still on track? Your digest is coming at 5pm. No need to peek.\n\n— Focus Mode"
    )
    msg["to"] = USER_EMAIL
    msg["from"] = USER_EMAIL
    msg["subject"] = "Focus check-in"
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    r = requests.post(
        f"{BASE}/messages/send",
        headers=HEADERS,
        json={"raw": raw},
        timeout=30,
    )
    r.raise_for_status()
    print("Nudge sent.")


def reverse():
    label_id = get_or_create_label()
    ids = []
    page_token = None
    while True:
        params = {"labelIds": [label_id], "maxResults": 100}
        if page_token:
            params["pageToken"] = page_token
        r = requests.get(f"{BASE}/messages", headers=HEADERS, params=params, timeout=30)
        r.raise_for_status()
        data = r.json()
        ids.extend(m["id"] for m in data.get("messages", []))
        page_token = data.get("nextPageToken")
        if not page_token:
            break
    if not ids:
        print("Nothing to reverse.")
        return
    for i in range(0, len(ids), 1000):
        chunk = ids[i : i + 1000]
        r = requests.post(
            f"{BASE}/messages/batchModify",
            headers=HEADERS,
            json={"ids": chunk, "removeLabelIds": [label_id], "addLabelIds": ["INBOX"]},
            timeout=60,
        )
        r.raise_for_status()
    print(f"Reversed {len(ids)} message(s) from '{LABEL_NAME}' back to inbox.")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    {"sweep": sweep, "nudge": nudge, "reverse": reverse}.get(
        cmd, lambda: sys.exit(f"Unknown command: {cmd!r}. Use sweep|nudge|reverse.")
    )()
