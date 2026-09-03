# Parent Health Agent

Family WhatsApp health companion — product app. This repo owns the landing
page, the backend API, and the database (source of truth for all
family/health data). Production WhatsApp onboarding is hosted directly by
the backend via the official Meta WhatsApp Cloud API — no local machine or
Hermes runtime is required for it to work. Hermes remains available as an
optional, locally-run alternative conversational layer for development and
experimentation (see the `hermes/` directory).

## Structure

- `apps/web` — Next.js landing page (family signup form)
- `apps/api` — FastAPI backend (families, members, onboarding, PostgreSQL via SQLAlchemy + Alembic)
- `hermes` — WhatsApp conversational layer: a Hermes skill (`hermes/skills/parent-health-onboarding`)
  and a thin backend client. Not the Hermes install itself — this is what gets copied into a
  running Hermes profile's `skills/` directory. See `hermes/skills/parent-health-onboarding/SKILL.md`.

## Backend setup

```bash
cd apps/api
python -m venv .venv
.venv/Scripts/activate        # or source .venv/bin/activate on macOS/Linux
pip install -r requirements.txt
cp ../../.env.example ../../.env   # then edit DATABASE_URL as needed
alembic upgrade head
uvicorn app.main:app --reload
```

Run tests:

```bash
pytest
```

## Frontend setup

```bash
cd apps/web
npm install
npm run dev
```

## MVP onboarding

After both family members verify their invitation links, the parent is asked a short flow:

1. Have you been diagnosed with diabetes by a doctor? — `Yes` or `No`
2. Are you currently taking any medication? — `Yes` or `No`
3. What time do you usually take your medicine? — free text such as `7 PM`

The third question is skipped when the medication answer is `No`. This same flow runs
whether the family reaches it through the hosted Meta webhook or a local Hermes
profile — both call the same `app/services/onboarding_service.py` functions.

## Hosted WhatsApp onboarding (Meta Cloud API)

Production WhatsApp messages are handled directly by `apps/api` via Meta's WhatsApp
Cloud API — see `app/routers/whatsapp_webhook.py` and
`app/services/whatsapp_webhook_service.py`. Routing is fully deterministic (no LLM
in this path): every inbound message is resolved against existing onboarding state
via `app/services/whatsapp_resolution_service.py`.

To enable it:

1. Create a Meta app with the WhatsApp product, and a phone number for it.
2. Set `WHATSAPP_PROVIDER=meta` and fill in the other `WHATSAPP_META_*` /
   `WHATSAPP_WEBHOOK_VERIFY_TOKEN` values from `.env.example` on the Render service.
3. In the Meta developer console, set the webhook callback URL to
   `https://<your-render-service>/whatsapp/webhook` and the verify token to the
   same value as `WHATSAPP_WEBHOOK_VERIFY_TOKEN`.
4. Subscribe the webhook to the `messages` field.

Inbound webhook events are deduplicated and rate-limited using the
`whatsapp_webhook_events` table (migration `0008`) — no raw phone numbers, message
text, tokens, or secrets are ever written to it or to application logs.

## Notes

- Phone numbers are stored internally in E.164 format (e.g. `+919876543210`).
- Health-related business logic lives under `apps/api/app/services/` so it can be
  called directly by both the hosted Meta webhook and Hermes, without duplicating logic.
- The app collects self-reported health information but does not provide medical advice,
  medication changes, dosing guidance, diagnosis, or food analysis.
- The Hermes skill under `hermes/` talks to the backend over HTTP via
  `backend_client.py`. It's an optional, locally-run alternative to the hosted
  webhook — not required for production.
- `/privacy`, `/terms`, and `/delete-data` on the web app describe what data is
  collected and how to request deletion.
