import type { Metadata } from "next";

import BrandHeader from "../../components/BrandHeader";
import styles from "../legal.module.css";

export const metadata: Metadata = {
  title: "Privacy Policy — Parent Health Agent",
  description: "What Parent Health Agent collects, why, and how to request deletion.",
};

export default function PrivacyPage() {
  return (
    <main className={styles.page}>
      <div className={styles.shell}>
        <BrandHeader />

        <section className={styles.card}>
          <span className={styles.eyebrow}>Privacy</span>
          <h1>Privacy Policy</h1>
          <p className={styles.updated}>Last updated: September 2026.</p>

          <div className={styles.prose}>
            <p>
              Parent Health Agent is a WhatsApp-based setup that helps a family record basic
              health information for a parent — currently focused on diabetes diagnosis,
              medication, and medicine timing. This page explains what we collect and why.
            </p>

            <h2>What we collect</h2>
            <ul>
              <li>Names and WhatsApp phone numbers for the parent and the family member who signs them up.</li>
              <li>A preferred language for the parent, captured during setup.</li>
              <li>Answers given during the WhatsApp setup conversation (currently: diabetes diagnosis, medication status, and medicine time).</li>
              <li>WhatsApp message metadata needed to route and reply to messages (such as delivery status and message identifiers) — not full message content or full phone numbers in our logs.</li>
            </ul>

            <h2>What we don&apos;t collect</h2>
            <ul>
              <li>We do not store full WhatsApp message text or phone numbers in application logs.</li>
              <li>We do not sell or share this information with advertisers.</li>
              <li>We do not provide medical advice, diagnosis, or medication guidance — the information collected supports family coordination, not clinical decisions.</li>
            </ul>

            <h2>Where it&apos;s stored</h2>
            <p>
              Data is stored in a hosted PostgreSQL database and processed by our backend
              service, both run by third-party infrastructure providers under standard
              access controls. WhatsApp messages are exchanged through Meta&apos;s WhatsApp
              Cloud API.
            </p>

            <h2>Who can see it</h2>
            <p>
              Only the family members you register (identified by their own verified WhatsApp
              number) can see their family&apos;s setup status through WhatsApp. Our team can
              access records only as needed to operate and support the service.
            </p>

            <h2>Your choices</h2>
            <p>
              You can ask us to delete your family&apos;s records at any time — see our{" "}
              <a href="/delete-data">data deletion page</a> for how that works.
            </p>

            <h2>Contact</h2>
            <p>
              Questions about this policy can be sent through the{" "}
              <a href="/delete-data">data deletion page</a>, which reaches the same team.
            </p>
          </div>
        </section>
      </div>
    </main>
  );
}
