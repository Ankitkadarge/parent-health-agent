# Parent Health Agent

Family WhatsApp health companion — product app. The WhatsApp runtime itself
is handled separately by Hermes; this repo owns the landing page, the
backend API, and the database (source of truth for all family/health data).

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

The third question is skipped when the medication answer is `No`.

## Notes

- Phone numbers are stored internally in E.164 format (e.g. `+919876543210`).
- Health-related business logic lives under `apps/api/app/services/` so it
  can be exposed to Hermes as callable tools later, without going through HTTP.
- The app collects self-reported health information but does not provide medical advice,
  medication changes, dosing guidance, diagnosis, or food analysis.
- The Hermes skill under `hermes/` talks to the backend over HTTP via
  `backend_client.py`; it has not yet been installed into a live Hermes
  profile or tested against a real WhatsApp conversation.
