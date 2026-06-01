---
name: Focus Mode Inbox
description: Reduces compulsive inbox checking for rudmilarahman@gmail.com by sweeping newsletter/forum mail out of the inbox into a 'Focus-Muted' label during focus hours, and sending a midday check-in nudge. Two subcommands - sweep, nudge - invoked from scheduled tasks. Label-only; never deletes mail.
---

# Focus Mode Inbox

Reduces distracted inbox checking by archiving low-priority mail during focus hours.

## Account
Hardcoded to Gmail account `e49b4b07-e6fc-4ec2-9dbc-f8385f577480` (rudmilarahman@gmail.com).

## What it does
- **sweep**: Lists all current inbox mail matching `category:forums OR list:*` (forums tab + anything with a List-Unsubscribe header — the standard newsletter signal). Removes the INBOX label and adds the `Focus-Muted` label. **Label-only via `messages/batchModify`. No emails are ever deleted** — they remain in All Mail and are still readable under the `Focus-Muted` label.
- **nudge**: Sends a short check-in email to self.

Why polling instead of a server-side filter: the connected Gmail OAuth scope does not include `gmail.settings.basic`, so filter creation returns 403. The sweep approach works with `gmail.modify`.

## Usage
```bash
uv run --with requests /workspace/.claude/skills/focus-mode-inbox/focus_mode.py sweep
uv run --with requests /workspace/.claude/skills/focus-mode-inbox/focus_mode.py nudge
```

## Schedule (managed via platform scheduler, America/Los_Angeles)
- sweep: `*/15 9-16 * * 1-5` — every 15 minutes, 9:00am–4:45pm PT, Mon–Fri.
- nudge: `0 14 * * 1-5` — 2:00pm PT, Mon–Fri.

After 5pm, the sweep stops running, so any new mail (including newsletters) lands in the inbox normally the next morning until the 9am sweep moves it.
