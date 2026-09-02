# Parent Health Agent

A family WhatsApp health companion. The repository owns the landing page,
verification flow, backend API, database schema, and the versioned Hermes skill.

## Production architecture

```text
Browser
  → Vercel / Next.js
  → Render / FastAPI
  → Supabase / PostgreSQL
```

Browser form submissions go through same-origin Next.js API routes. The browser
does not connect directly to Supabase, and raw invitation tokens are never stored
in PostgreSQL.

## Structure

- `apps/web` — Next.js landing page and verification pages
- `apps/api` — FastAPI backend, SQLAlchemy models, Alembic migrations, tests
- `hermes` — versioned WhatsApp conversational skill and backend client

The `hermes` folder is not the live Hermes installation. Copy the skill into the
active Hermes profile and merge the scoped persona guidance from `hermes/SOUL.md`.

## Backend setup

```bash
cd apps/api
python -m venv .venv
.venv/Scripts/activate        # Windows
# source .venv/bin/activate   # macOS/Linux
python -m pip install -r requirements.txt
cp ../../.env.example ../../.env
alembic upgrade head
uvicorn app.main:app --reload
```

Useful endpoints:

```text
GET /          service information
GET /health    process health
GET /ready     process + database readiness
GET /docs      interactive API documentation
```

Run the backend checks:

```bash
python -m pip check
python -m compileall -q app
pytest -q
```

## Frontend setup

```bash
cd apps/web
npm ci
npm run typecheck
npm run build
npm run dev
```

`API_BASE_URL` is the preferred server-only Vercel variable. The legacy
`NEXT_PUBLIC_API_BASE_URL` remains a temporary fallback, but browser code no
longer calls Render directly.

## Signup and verification

1. The child submits two distinct consenting WhatsApp numbers.
2. FastAPI stores the family, members, WhatsApp identities, and one-time invites.
3. Each person opens their own verification link and enters the matching number.
4. After both verify, the family moves to onboarding.

Invitation tokens are returned once in the signup response and stored only as
SHA-256 digests in PostgreSQL.

## MVP onboarding

The parent is asked:

1. Have you been diagnosed with diabetes by a doctor? — `Yes` or `No`
2. Are you currently taking any medication? — `Yes` or `No`
3. What time do you usually take your medicine? — free text such as `7 PM`

The third question is skipped when the medication answer is `No`.

## Optional WhatsApp group creation

Group creation depends on a separately hosted and access-controlled WhatsApp
bridge. It is disabled by default so bridge downtime can never slow or break
family signup.

Enable it only when the bridge is continuously hosted:

```text
WHATSAPP_GROUP_CREATION_ENABLED=true
WHATSAPP_BRIDGE_BASE_URL=https://your-secure-bridge.example
```

## Reset disposable test data

The reset script preserves the schema, migrations, RLS, and configuration.

Dry run:

```bash
cd apps/api
python scripts/reset_test_data.py
```

Delete all application rows:

```bash
python scripts/reset_test_data.py --confirm DELETE-ALL-TEST-DATA
```

Never run the confirmed command against a database containing real family data.

## Safety and privacy

- Phone numbers are normalized to E.164.
- Child and parent numbers must be different.
- Public Supabase roles have no direct table access.
- RLS is enabled as a deny-by-default boundary.
- The app collects self-reported information only.
- It does not provide diagnosis, dosing, medication changes, or medical advice.
