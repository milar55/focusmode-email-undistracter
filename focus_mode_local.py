#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "google-api-python-client",
#     "google-auth-oauthlib",
#     "google-auth-httplib2",
#     "requests"
# ]
# ///
"""Focus-mode inbox tooling (Local Version).

Authenticates with standard Google OAuth2 client credentials.
Requires 'credentials.json' from Google Cloud Console.

Two subcommands:
  sweep  - Move matching inbox mail from the last 24 hours (forums tab +
           List-Unsubscribe newsletters) out of the inbox and into the
           `Focus-Muted` label. Label-only; emails are NEVER deleted.
  nudge  - Send a midday check-in email to self.
  reverse - Restore all messages with `Focus-Muted` label back to the Inbox.
"""
import base64
import os
import sys
from email.mime.text import MIMEText

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]

USER_EMAIL = "rudmilarahman@gmail.com"
LABEL_NAME = "Focus-Muted"
SWEEP_QUERY = "in:inbox newer_than:2h (category:forums OR list:*)"


def get_gmail_service():
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first time.
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists("credentials.json"):
                print("Error: 'credentials.json' not found.", file=sys.stderr)
                print("Please download it from the Google Cloud Console (APIs & Services > Credentials > OAuth Client ID > Desktop App) and place it in this folder.", file=sys.stderr)
                sys.exit(1)
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
        
        # Save the credentials for the next run
        with open("token.json", "w") as token:
            token.write(creds.to_json())

    try:
        return build("gmail", "v1", credentials=creds)
    except Exception as e:
        print(f"Error building Gmail service: {e}", file=sys.stderr)
        sys.exit(1)


def get_or_create_label(service):
    try:
        results = service.users().labels().list(userId="me").execute()
        labels = results.get("labels", [])
        for lbl in labels:
            if lbl["name"] == LABEL_NAME:
                return lbl["id"]
        
        # Create label
        label_body = {
            "name": LABEL_NAME,
            "labelListVisibility": "labelShow",
            "messageListVisibility": "show",
        }
        lbl = service.users().labels().create(userId="me", body=label_body).execute()
        return lbl["id"]
    except HttpError as error:
        print(f"API Error in get_or_create_label: {error}", file=sys.stderr)
        sys.exit(1)


def sweep(service):
    label_id = get_or_create_label(service)
    messages = []
    page_token = None
    try:
        while True:
            results = service.users().messages().list(
                userId="me", q=SWEEP_QUERY, pageToken=page_token, maxResults=100
            ).execute()
            messages.extend(results.get("messages", []))
            page_token = results.get("nextPageToken")
            if not page_token:
                break
    except HttpError as error:
        print(f"API Error in listing messages: {error}", file=sys.stderr)
        sys.exit(1)

    if not messages:
        print("Nothing to sweep.")
        return

    ids = [m["id"] for m in messages]
    # batchModify accepts up to 1000 ids per call
    for i in range(0, len(ids), 1000):
        chunk = ids[i : i + 1000]
        body = {
            "ids": chunk,
            "removeLabelIds": ["INBOX"],
            "addLabelIds": [label_id],
        }
        try:
            service.users().messages().batchModify(userId="me", body=body).execute()
        except HttpError as error:
            print(f"API Error in batchModify: {error}", file=sys.stderr)
            sys.exit(1)
            
    print(f"Swept {len(ids)} message(s) out of inbox into '{LABEL_NAME}'.")


def nudge(service):
    msg = MIMEText(
        "Still on track? Your digest is coming at 5pm. No need to peek.\n\n— Focus Mode"
    )
    msg["to"] = USER_EMAIL
    msg["from"] = USER_EMAIL
    msg["subject"] = "Focus check-in"
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    
    try:
        service.users().messages().send(userId="me", body={"raw": raw}).execute()
        print("Nudge sent.")
    except HttpError as error:
        print(f"API Error in sending nudge: {error}", file=sys.stderr)
        sys.exit(1)


def reverse(service):
    label_id = get_or_create_label(service)
    messages = []
    page_token = None
    try:
        while True:
            results = service.users().messages().list(
                userId="me", labelIds=[label_id], pageToken=page_token, maxResults=100
            ).execute()
            messages.extend(results.get("messages", []))
            page_token = results.get("nextPageToken")
            if not page_token:
                break
    except HttpError as error:
        print(f"API Error in listing messages: {error}", file=sys.stderr)
        sys.exit(1)

    if not messages:
        print("Nothing to reverse.")
        return

    ids = [m["id"] for m in messages]
    # batchModify accepts up to 1000 ids per call
    for i in range(0, len(ids), 1000):
        chunk = ids[i : i + 1000]
        body = {
            "ids": chunk,
            "removeLabelIds": [label_id],
            "addLabelIds": ["INBOX"],
        }
        try:
            service.users().messages().batchModify(userId="me", body=body).execute()
        except HttpError as error:
            print(f"API Error in batchModify: {error}", file=sys.stderr)
            sys.exit(1)
            
    print(f"Reversed {len(ids)} message(s) from '{LABEL_NAME}' back to inbox.")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd not in ("sweep", "nudge", "reverse"):
        sys.exit(f"Unknown command: {cmd!r}. Use sweep|nudge|reverse.")
        
    service = get_gmail_service()
    if cmd == "sweep":
        sweep(service)
    elif cmd == "nudge":
        nudge(service)
    elif cmd == "reverse":
        reverse(service)
