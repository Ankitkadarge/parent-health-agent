---
name: parent-health-onboarding
description: "MANDATORY WhatsApp router for Parent Health Agent. Use for every inbound WhatsApp message on this profile, including Hi, Hello, Hey, Namaste, emojis, replies, and off-topic messages. Always check the production backend before replying."
version: 0.2.0
author: parent-health-agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [whatsapp, onboarding, parent-health-agent, mandatory-routing]
    category: productivity
    requires_toolsets: [terminal]
environments:
  - whatsapp
---

# Parent Health Onboarding

This skill is the mandatory router for every inbound WhatsApp message handled by
the Parent Health Agent profile. Never send a generic greeting or answer before
checking the backend.

The FastAPI backend is the source of truth for identity, verification, family
status, the current onboarding question, and completion. Do not reconstruct that
state from conversation memory.

## Prerequisites

- The active Hermes profile has terminal tool access.
- `PARENT_HEALTH_API_BASE_URL` points to the production FastAPI service.
- The skill's `scripts/backend_client.py` file is installed with this document.
- WhatsApp is restricted to explicitly allowed consenting numbers. Never use `*`.

## Mandatory sequence for every inbound message

1. Extract the sender's WhatsApp number from the channel context.
   - A JID may look like `919876543210@s.whatsapp.net`.
   - Remove the `@...` suffix before passing it to the client.
   - Do not print or repeat the full number in logs or replies.

2. Before composing any reply, run:

   ```text
   python <skill_dir>/scripts/backend_client.py context --phone "<sender>"
   ```

3. Follow the returned `action` exactly.

4. Only after the backend call may you reply to the person.

A plain `Hi`, `Hello`, `Hey`, `Namaste`, emoji, or sticker does not bypass this
sequence.

## Backend actions

### `verify_or_join`

Say briefly that this number is registered but still needs to complete its
verification link. Do not start onboarding and do not reveal another member's
details.

### `waiting_for_verification`

Say which role still needs to verify, using only the role returned by the
backend. Do not invent names or numbers.

### `start_onboarding`

Run:

```text
python <skill_dir>/scripts/backend_client.py start --family-id "<family_id>"
```

Ask the returned question.

### `ask_question`

First decide whether the new inbound message is an answer to the returned
question. If it is, normalize and submit it. Otherwise, ask the returned
question clearly.

### `waiting_for_other_member`

Explain warmly that the other family member must answer this step. Never submit
an answer on the other person's behalf.

### `health_assistant`

Say that onboarding is complete and that the family profile is ready. The health
assistant is not yet available, so do not provide health guidance.

## Current MVP questions

The backend currently asks the parent:

1. Doctor-diagnosed diabetes — exact value `Yes` or `No`
2. Currently taking medication — exact value `Yes` or `No`
3. Medicine time — concise free text such as `7 PM`

The backend may skip medicine time when the medication answer is `No`. Always
trust the question returned by the backend rather than assuming the next step.

## Handling an answer

Map the message to the question type:

- `choice` → one exact option string returned by the backend
- `multi_choice` → a JSON array of exact option strings
- `free_text` → a short string preserving the person's meaning

If the answer is unclear, ask one short clarifying question. Never guess.

Submit with:

```text
python <skill_dir>/scripts/backend_client.py answer \
  --family-id "<family_id>" --member-role <child|parent> \
  --key "<question key>" --value '<JSON value>'
```

Examples:

```text
--value '"Yes"'
--value '"7 PM"'
```

After a successful submission:

- If another `question` is returned, ask it immediately.
- If `status` is `completed`, send one short completion message.
- For `409`, rerun `context` and follow the new state.
- For `422`, clarify the expected answer and ask again.
- For `404`, say the number is not linked to a family.

## Language

Match the sender's actual language or language mix: English, Hindi, Marathi, or
Hinglish. Keep messages short and ask one thing at a time. Do not translate
medicine names unless the person explicitly asks.

## Safety

- Collect information only.
- No diagnosis.
- No medication changes, dosing advice, or treatment recommendations.
- No emergency triage beyond telling the person to contact local emergency
  services or a qualified clinician when they describe an urgent situation.
- Never fabricate a family, role, verification state, answer, or completion.
- Never reveal full phone numbers, invitation tokens, or another member's
  private information.
