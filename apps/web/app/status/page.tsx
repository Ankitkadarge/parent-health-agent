import styles from "./status.module.css";

export const dynamic = "force-dynamic";

type ApiReadiness = {
  status?: string;
  database?: string;
};

type WhatsAppStatus = {
  provider?: string;
  enabled?: boolean;
  configured?: boolean;
  auto_start_enabled?: boolean;
  auto_start_configured?: boolean;
  processed_events?: number;
  failed_events?: number;
  last_event_status?: string | null;
  last_event_at?: string | null;
};

const API_BASE_URL = (
  process.env.API_BASE_URL ??
  process.env.NEXT_PUBLIC_API_BASE_URL ??
  "https://parent-health-api.onrender.com"
).replace(/\/$/, "");

async function readJson<T>(path: string): Promise<T | null> {
  try {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      cache: "no-store",
      signal: AbortSignal.timeout(20_000),
    });
    if (!response.ok) return null;
    return (await response.json()) as T;
  } catch {
    return null;
  }
}

function StatusRow({
  label,
  ok,
  detail,
}: {
  label: string;
  ok: boolean;
  detail: string;
}) {
  return (
    <div className={styles.row}>
      <span className={ok ? styles.ok : styles.pending} aria-hidden="true">
        {ok ? "✓" : "!"}
      </span>
      <div>
        <strong>{label}</strong>
        <p>{detail}</p>
      </div>
    </div>
  );
}

export default async function StatusPage() {
  const [readiness, whatsapp] = await Promise.all([
    readJson<ApiReadiness>("/ready"),
    readJson<WhatsAppStatus>("/whatsapp/cloud/status"),
  ]);

  const apiReady =
    readiness?.status === "ready" && readiness.database === "ok";
  const whatsappReady =
    whatsapp?.configured === true &&
    whatsapp.auto_start_configured === true;
  const publicBetaReady = apiReady && whatsappReady;

  return (
    <main className={styles.page}>
      <section className={styles.card}>
        <a className={styles.back} href="/">
          ← Parent Health Agent
        </a>
        <p className={styles.eyebrow}>Live readiness</p>
        <h1>Public beta status</h1>
        <p className={styles.intro}>
          This page reports non-secret production readiness. It never displays
          phone numbers, tokens, or health answers.
        </p>

        <div className={styles.rows}>
          <StatusRow
            label="Landing page and signup"
            ok
            detail="The public Vercel experience is deployed."
          />
          <StatusRow
            label="API and Supabase database"
            ok={apiReady}
            detail={
              apiReady
                ? "Render can reach the production database."
                : "The API or database readiness check is unavailable."
            }
          />
          <StatusRow
            label="Hosted WhatsApp onboarding"
            ok={whatsappReady}
            detail={
              whatsappReady
                ? "Meta Cloud API credentials and automatic onboarding are configured."
                : "Meta WhatsApp Cloud API credentials, webhook, or onboarding template still need configuration."
            }
          />
          <StatusRow
            label="Unrestricted public beta"
            ok={publicBetaReady}
            detail={
              publicBetaReady
                ? "Cloud prerequisites are configured. Complete a real acceptance test before broad promotion."
                : "Keep testing controlled until hosted WhatsApp onboarding is configured."
            }
          />
        </div>

        {whatsapp && (
          <div className={styles.metrics}>
            <span>Processed webhook events: {whatsapp.processed_events ?? 0}</span>
            <span>Failed webhook events: {whatsapp.failed_events ?? 0}</span>
            <span>
              Last event: {whatsapp.last_event_status ?? "none yet"}
            </span>
          </div>
        )}
      </section>
    </main>
  );
}
