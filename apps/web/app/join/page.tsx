import type { Metadata } from "next";
import Link from "next/link";

import JoinForm from "./JoinForm";
import styles from "./join.module.css";

export const metadata: Metadata = {
  title: "Verify your WhatsApp number — Parent Health Agent",
  description: "Verify a family invitation for Parent Health Agent.",
};

type JoinPageProps = {
  searchParams: Promise<{ token?: string | string[] }>;
};

export default async function JoinPage({ searchParams }: JoinPageProps) {
  const params = await searchParams;
  const rawToken = params.token;
  const token = Array.isArray(rawToken) ? rawToken[0] ?? "" : rawToken ?? "";

  return (
    <main className={styles.page}>
      <div className={styles.shell}>
        <Link className={styles.brand} href="/" aria-label="Back to Parent Health Agent">
          <span className={styles.brandMark} aria-hidden="true">
            <svg viewBox="0 0 24 24" fill="none">
              <path
                d="M12 3c2.8 3.2 4.7 5.8 4.7 8.5A4.7 4.7 0 0 1 12 16.2a4.7 4.7 0 0 1-4.7-4.7C7.3 8.8 9.2 6.2 12 3Z"
                fill="currentColor"
              />
              <path
                d="M7 18.2c1.5 1.4 3.2 2.1 5 2.1s3.5-.7 5-2.1"
                stroke="currentColor"
                strokeWidth="1.7"
                strokeLinecap="round"
              />
            </svg>
          </span>
          <span>Parent Health Agent</span>
        </Link>

        <section className={styles.card}>
          <div className={styles.eyebrow}>One-time family verification</div>
          <h1>Verify your WhatsApp number</h1>
          <p className={styles.intro}>
            Enter the same WhatsApp number that was used when this family was registered.
            This prevents someone else from using your invitation link.
          </p>

          <JoinForm token={token} />
        </section>

        <p className={styles.privacy}>
          Parent Health Agent uses this number only to match you with the correct family
          invitation. It does not provide medical advice.
        </p>
      </div>
    </main>
  );
}
