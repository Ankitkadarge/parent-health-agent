# Parent Health Agent

A family WhatsApp health companion. The repository owns the landing page,
verification flow, backend API, database schema, hosted WhatsApp webhook, and
the versioned Hermes development skill.

## Production architecture

```text
Browser
  → Vercel / Next.js
  → Render / FastAPI
  → Supabase / PostgreSQL

WhatsApp
  → Meta WhatsApp Cloud API
  → Render / FastAPI webhook
  → Supabase / PostgreSQL
  → Meta WhatsApp Cloud API reply
```

Browser form submissions go through same-origin Next.js API routes. The browser
does not connect directly to Supabase, and raw invitation tokens are never stored
in PostgreSQL.

The hosted Meta webhook is the production transport. Hermes remains useful for
local development, but public beta traffic must not depend on a laptop, WhatsApp
Web session, or temporary tunnel.

## Structure

- `apps/web` — Next.js landing page, verification pages, and status page
- `apps/api` — FastAPI backend, SQLAlchemy models, Alembic migrations, tests
- `hermes` — versioned local-development conversational skill and backend client

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
GET /                         service information
GET /health                   process health
GET /ready                    process + database readiness
GET /docs                     interactive API documentation
GET /whatsapp/cloud/status    non-secret hosted-WhatsApp readiness
GET /whatsapp/cloud/webhook   Meta webhook verification handshake
POST /whatsapp/cloud/webhook  signed Meta message events
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
5. When Meta auto-start is configured, the parent receives an approved WhatsApp
   template asking them to reply `START` or `HI`.
6. The hosted webhook then asks and saves each onboarding question automatically.

Invitation tokens are returned once in the signup response and stored only as
SHA-256 digests in PostgreSQL.

## MVP onboarding

The parent is asked:

1. Have you been diagnosed with diabetes by a doctor? — `Yes` or `No`
2. Are you currently taking any medication? — `Yes` or `No`
3. What time do you usually take your medicine? — free text such as `7 PM`

The third question is skipped when the medication answer is `No`.

The hosted webhook accepts common English and Indian-language yes/no variants,
but stores only the canonical values `Yes` and `No`.

## Meta WhatsApp Cloud API setup

The code is provider-ready, but Meta account ownership and secrets must be
configured by the account owner.

1. Create or open a Meta app with the WhatsApp product and attach a production
   WhatsApp Business number.
2. Generate a permanent system-user access token with the required WhatsApp
   messaging permissions. Do not use the temporary API Setup token in production.
3. Create an approved utility template named, for example,
   `parent_health_onboarding_start`. A safe body is:

   ```text
   Your Parent Health Agent setup is ready. Reply START to answer three short
   setup questions. This service does not provide medical advice.
   ```

4. Add these variables to the Render service:

   ```text
   WHATSAPP_CLOUD_ENABLED=true
   WHATSAPP_CLOUD_VERIFY_TOKEN=<random secret chosen by you>
   WHATSAPP_CLOUD_APP_SECRET=<Meta app secret>
   WHATSAPP_CLOUD_ACCESS_TOKEN=<permanent system-user token>
   WHATSAPP_CLOUD_PHONE_NUMBER_ID=<Meta phone-number ID>
   WHATSAPP_CLOUD_GRAPH_VERSION=v25.0
   WHATSAPP_CLOUD_LANDING_URL=https://parent-health-agent.vercel.app
   WHATSAPP_CLOUD_AUTO_START_ENABLED=true
   WHATSAPP_CLOUD_ONBOARDING_TEMPLATE_NAME=parent_health_onboarding_start
   WHATSAPP_CLOUD_ONBOARDING_TEMPLATE_LANGUAGE=en_US
   ```

5. In Meta's WhatsApp webhook configuration, use:

   ```text
   Callback URL:
   https://parent-health-api.onrender.com/whatsapp/cloud/webhook

   Verify token:
   the exact WHATSAPP_CLOUD_VERIFY_TOKEN value
   ```

6. Subscribe the app to the WhatsApp `messages` webhook field.
7. Open `/whatsapp/cloud/status`; `configured` and
   `auto_start_configured` should both be `true`.
8. Complete one real consenting family flow before opening the beta broadly.

Incoming webhook POSTs are authenticated with Meta's
`X-Hub-Signature-256` HMAC. The event ledger stores no raw prompt text and no
plain sender number; it stores a one-way sender hash and operational metadata for
idempotency and debugging.

## Optional local WhatsApp group creation

Group creation depends on a separately hosted and access-controlled WhatsApp
bridge. It is disabled by default so bridge downtime can never slow or break
family signup.

Enable it only when the bridge is continuously hosted:

```text
WHATSAPP_GROUP_CREATION_ENABLED=true
WHATSAPP_BRIDGE_BASE_URL=https://your-secure-bridge.example
```

This local bridge is separate from the hosted Meta webhook and is not required
for production onboarding.

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
- Meta webhook POSTs require an app-secret signature.
- Duplicate webhook deliveries are ignored by provider message ID.
- Operational event records store no raw message text or plain sender number.
- The app collects self-reported information only.
- It does not provide diagnosis, dosing, medication changes, or medical advice.
