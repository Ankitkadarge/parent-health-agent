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

## Notes

- Phone numbers are stored internally in E.164 format (e.g. `+919876543210`).
- Health-related business logic lives under `apps/api/app/services/` so it
  can be exposed to Hermes as callable tools later, without going through HTTP.
- No medical advice, medication logic, or food analysis is implemented yet.
- The Hermes skill under `hermes/` talks to the backend over HTTP via
  `backend_client.py`; it has not yet been installed into a live Hermes
  profile or tested against a real WhatsApp conversation.
