---
name: whatsapp-context-debug
description: "TEMPORARY diagnostic skill — reports which sender/session identifier fields Hermes actually exposes for an inbound WhatsApp message. Uninstall after use."
version: 0.1.0
author: parent-health-agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [whatsapp, diagnostic, temporary, debug]
    category: debug
    requires_toolsets: []
environments:
  - whatsapp
---

# WhatsApp Context Debug (TEMPORARY)

**This is a throwaway diagnostic tool, not a real feature.** Its only job is to answer
one question empirically: when a WhatsApp message reaches you through Hermes, what
sender/session identity fields are actually visible to you, and under what names?
Once you have that answer, remove this skill (see "Uninstall" below) — do not leave
it running.

## Why this exists

The parent-health-onboarding skill needs to know the sender's phone number every
turn, but the exact field Hermes uses to expose that isn't documented publicly.
Rather than guess a field name and find out it's wrong in production, this skill
makes the live bot say back exactly what it can see.

## Hard rules — read before doing anything else

1. **Only report what is already present in your own ambient context for this
   turn** — the message/session metadata Hermes hands you as part of receiving this
   WhatsApp message. Do not go looking for it.
2. **Do not use any tool to find identity information** — no `terminal`, no
   `read_file`, no file search, no environment variable dump. Do not open, list, or
   read anything under the Hermes home directory (config, `.env`, `auth.json`,
   `whatsapp/session/`, `state.db`, logs, or any other file). If you'd need a tool
   call to find something, it's out of scope for this skill — say so instead of
   fetching it.
3. **Never report:** API keys, tokens, passwords, session credentials, file
   contents, file paths under the Hermes home directory, environment variable
   values, or the content of any other message (this one or past ones — no message
   history, no conversation transcript).
4. **When in doubt, omit it.** This skill exists to find an identifier, not to prove
   how much context you have access to. If something might be sensitive and isn't
   clearly an identifier, leave it out and note that you left it out.

## What to look for

Inspect exactly what you were given for this message and look for any field that
identifies *who sent it* or *which conversation it belongs to* — using whatever name
it actually has, not the names below. These are examples of what such a field might
be called, not a list to force-match against:

- `user_id`, `sender_id`, `from`, `chat_id`, `conversation_id`
- a WhatsApp JID (typically looks like `919876543210@s.whatsapp.net` or
  `919876543210@lid`)
- a raw phone number, in any format
- any other stable per-contact or per-conversation identifier you can see, under
  whatever name it has

If none of these exist under any name, say that plainly — don't invent one.

## How to Run

1. When a WhatsApp message arrives while this skill is active, do not treat it as a
   normal conversation. Instead, look at everything in your immediate context for
   this turn: system/preamble text, structured metadata, tool-call results that were
   already provided to you (not ones you fetch) — anything Hermes gave you about
   this message besides its text content.
2. For each field you find that looks identity-related (per "What to look for"
   above), record: its exact name, its exact value, and one line on where you saw it
   (e.g. "in the system preamble before the user message" / "in a `message.from`
   field").
3. Apply the redaction rule: if a field's name contains (case-insensitively) any of
   `token`, `secret`, `key`, `auth`, `session`, `credential`, or `password`, or its
   value is a long random-looking blob (roughly 20+ characters of hex/base64), still
   report that the field exists but replace its value with `[REDACTED]`.
4. Reply to the sender with a plain-text report in this shape:

   ```
   [context-debug]
   Fields found:
   - <field name>: <value or [REDACTED]>
   - <field name>: <value or [REDACTED]>
   (list every field you found; if none, say "No identity-shaped fields found in this turn's context.")

   Best candidate for a stable sender identifier: <field name>, value: <value>
   (or: "No clear candidate found.")
   ```

5. Do nothing else. Don't try to answer onboarding questions, don't call the
   parent-health-agent backend, don't attempt anything conversational beyond this
   report.

## Install (Windows, PowerShell)

Copies this file into your live Hermes skills directory. This only adds a new file
under Hermes's *data* directory (where skills already live, alongside its bundled
ones) — it does not touch any Hermes source code or existing configuration.

```powershell
$dest = "$env:LOCALAPPDATA\hermes\skills\debug\whatsapp-context-debug"
New-Item -ItemType Directory -Path $dest -Force | Out-Null
Copy-Item "C:\Users\Ankit\parent-health-agent\hermes\skills\whatsapp-context-debug\SKILL.md" -Destination $dest -Force
```

## Uninstall (Windows, PowerShell)

```powershell
Remove-Item -Recurse -Force "$env:LOCALAPPDATA\hermes\skills\debug\whatsapp-context-debug"
```

## Safety note on deploying this at all

This skill makes the bot **echo internal message metadata back to whoever messages
it**. That's fine for a controlled, one-off test from your own phone number. It is
not fine to leave running on a number that might receive messages from anyone else —
it would hand a stranger a peek at your bot's internal field names. Test it, capture
the answer, then uninstall it the same session.

## Notes on what's still unverified

- Whether Hermes hot-reloads new skill files into an already-running bot session, or
  needs the gateway/bot restarted, isn't confirmed. If the bot doesn't seem to know
  about this skill after copying it in, try restarting the Hermes gateway/bot
  process before assuming the skill itself is broken.
- The `category: debug` and `environments: [whatsapp]` frontmatter values follow the
  pattern seen in Hermes's own bundled skills, but aren't confirmed to be a fixed,
  validated list — if Hermes rejects or ignores this file, that frontmatter is the
  first thing to check.
