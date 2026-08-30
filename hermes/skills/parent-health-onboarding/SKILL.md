---
name: parent-health-onboarding
description: "Conversational onboarding for the parent-health-agent WhatsApp bot: greets the sender, asks the structured onboarding questions in their language, and submits answers to the backend."
version: 0.1.0
author: parent-health-agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [whatsapp, onboarding, parent-health-agent]
    category: productivity
    requires_toolsets: [terminal]
environments:
  - whatsapp
---

# Parent Health Onboarding

Conversational layer for the parent-health-agent onboarding flow. All business logic —
what question is current, whether an answer is valid, when onboarding is complete —
lives in the FastAPI backend. This skill only decides *how to say things* and *when to
call the backend*. Never compute onboarding state yourself; always ask the backend.

**Verify one assumption before relying on it:** the exact field Hermes uses to expose
the inbound WhatsApp sender's phone number on this channel is not confirmed against
live documentation. The first time this skill runs on a real message, check what the
message context actually contains (it should be a WhatsApp JID or E.164-shaped number)
before trusting a specific field name here.

## When to Use

Use this skill for every inbound WhatsApp message on a number connected to
parent-health-agent, for the entire lifetime of a conversation with that sender —
both during onboarding and after, since the backend (not this skill) decides
whether the sender should be treated as still onboarding or as a completed family.

## Prerequisites

- `terminal` tool access, to run the backend client script.
- `PARENT_HEALTH_API_BASE_URL` set in the environment (see `hermes/.env.example` in
  the parent-health-agent repo). Defaults to `http://127.0.0.1:8000` if unset.
- The FastAPI backend running and reachable at that URL.

## How to Run

1. **Identify the sender.** Read the sender's phone number from the inbound WhatsApp
   message context for this channel. It may need light cleanup (WhatsApp JIDs look
   like `919876543210@s.whatsapp.net` — strip the `@...` suffix before passing it on).
   You do not need to normalize to E.164 yourself; the backend does that and will
   reject anything it can't parse.

2. **Get context.** Run:
   ```
   python <skill_dir>/scripts/backend_client.py context --phone "<sender phone>"
   ```
   - If the response has `"error": true, "status": 404` — this number isn't linked to
     any family yet. Reply briefly that you don't recognize this number and can't help
     yet (do not guess who they are or invent a family).
   - If the response has `"error": true, "status": 422` — the phone number couldn't be
     parsed. Say so plainly and ask them to confirm the number they're messaging from.
   - Otherwise, branch on `action` (step 3).

3. **Branch on `action`:**

   - **`start_onboarding`** — Run:
     ```
     python <skill_dir>/scripts/backend_client.py start --family-id "<family_id>"
     ```
     Take the `question` from the response and ask it (see "Asking a Question" below).

   - **`ask_question`** — Ask the `question` in the response directly (see "Asking a
     Question" below). This is also where a reply to a *previous* question gets
     processed — see "Handling an Answer" below. Don't just re-ask the same question
     every turn; check whether the sender's message is an answer to it first.

   - **`waiting_for_other_member`** — The current step needs the **other** family
     member (`target_role`), not this sender. Reply briefly and warmly explaining
     that you're waiting to hear from the {target_role} for this step, and do **not**
     accept or forward an answer from this sender for it — even if they try to answer
     on the other person's behalf. This is a hard rule, not a suggestion: only the
     `member_role` matching `target_role` may answer this step, and only the backend's
     `/onboarding/answer` endpoint enforces it — this skill enforces it too, first,
     so the sender gets a clear, kind explanation instead of a raw rejection.

   - **`health_assistant`** — Onboarding is complete for this family. For now, reply
     that onboarding is done and you'll be in touch — do **not** attempt health
     coaching, medical advice, or medication guidance. That's a future milestone.

## Asking a Question

The `question` object always has: `key`, `target` (`child`/`parent` — who should
answer), `type` (`choice` / `multi_choice` / `free_text`), `prompt`, and `options`
(present for `choice`/`multi_choice`, `null` for `free_text`).

- Translate/phrase the `prompt` naturally in the sender's language (see Language
  Behavior below) — don't read it verbatim if it reads stiffly in that language.
- For `choice`/`multi_choice`, present the `options` as a short numbered or bulleted
  list so a reply like "2" or "Diabetes and thyroid" is easy to map back to exact
  option strings. Keep every option's *English* label recognizable even when the
  surrounding message is in Hindi/Marathi/Hinglish — these are stored as exact
  strings on the backend and must match one of `options` exactly.

## Handling an Answer

When the sender's message is answering the current question (not a new topic):

1. Map their natural-language reply to a normalized value matching the question's
   `type`:
   - `choice` → exactly one string from `options`, matched exactly (fix casing/typos
     yourself, but the final value must equal one of the listed options).
   - `multi_choice` → a JSON array of exact strings from `options`. If they name
     something not in `options`, use the closest listed option, or `"Other"` if the
     list has one — don't invent a new option string.
   - `free_text` → a concise value that preserves their meaning. Don't pad it, don't
     translate medication or drug names unless the sender clearly intends a
     translation (e.g. they explicitly ask "how do you say this in English").
   - If the reply doesn't map cleanly (too vague, off-topic, or a question of their
     own), don't guess — ask a brief clarifying follow-up instead of submitting a
     low-confidence value.

2. Submit it:
   ```
   python <skill_dir>/scripts/backend_client.py answer \
     --family-id "<family_id>" --member-role <child|parent> \
     --key "<current question key>" --value '<JSON value>'
   ```
   `--value` must be JSON: a quoted string (`'"Hindi"'`) for `choice`/`free_text`, or
   a JSON array (`'["Diabetes", "Thyroid"]'`) for `multi_choice`.

3. Handle the response:
   - `"error": true, "status": 422` — the value was invalid (wrong option, wrong
     role, empty free text). Re-ask the same question, clarifying what's expected.
   - `"error": true, "status": 409` — step mismatch, already answered differently, or
     onboarding not started/already completed. Re-run `context` and follow whatever
     it now reports rather than guessing what went wrong.
   - Success with a `question` present — immediately ask that next question. Don't
     wait for the sender to prompt you.
   - Success with `"status": "completed"` (`question` is `null`) — send a short,
     warm completion message. Don't ask anything further.

## Language Behavior

- Understand and reply naturally in English, Hindi, Marathi, and code-switched
  Hinglish, matching the sender's own style (if they write in Hinglish, reply in
  Hinglish; don't force pure Hindi or pure English on them).
- Once a family's `preferred_language` is known (surfaced via `/whatsapp/resolve` if
  you need it explicitly), lean toward that language for the *parent's* messages —
  but always mirror whatever language the sender is actually using in the moment
  over a stored preference.
- Don't translate medication names, brand names, or medical terms unless the sender
  is clearly asking for a translation.
- Keep every message short. These are parents and their adult children on WhatsApp,
  not a chat window — avoid long paragraphs, avoid jargon, one question at a time.

## Safety

- No medical advice, no diagnosis, no medication changes or dosing guidance — at any
  point, not just during onboarding. This skill only collects structured onboarding
  answers.
- If the sender asks a health question before onboarding is complete, briefly say
  onboarding needs to finish first, then return to the current question.
- If the sender asks a health question after onboarding is complete
  (`action: health_assistant`), say that health guidance isn't available yet — don't
  attempt to answer it, even a little.
- Never fabricate a family, member, role, or answer. Every fact you state about the
  family (name, role, current step) must come from a backend response, not from
  guessing or from earlier turns you didn't just verify.

## Pitfalls

- **Re-deriving onboarding state.** Don't track "what step we're on" in conversation
  memory across turns — always re-fetch `/whatsapp/context` and trust it, since the
  backend is the source of truth and may have changed (e.g. the other family member
  answered in the meantime).
- **Answering on someone else's behalf.** If the sender tries to answer a question
  targeted at the other role, don't submit it — that's exactly the
  `waiting_for_other_member` case, and the backend would reject it anyway (422), but
  catching it here first avoids a confusing raw error reaching the sender.
- **Inventing option strings.** `choice`/`multi_choice` values must exactly match one
  of the question's `options`, or the backend returns 422. When in doubt, ask.
- **Skipping the language match.** Replying in English to a Hindi/Hinglish message
  reads as cold and defeats the point of this bot for a non-English-first parent.
