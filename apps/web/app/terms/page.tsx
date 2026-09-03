import type { Metadata } from "next";

import BrandHeader from "../../components/BrandHeader";
import styles from "../legal.module.css";

export const metadata: Metadata = {
  title: "Terms of Use — Parent Health Agent",
  description: "The terms for using Parent Health Agent's WhatsApp family health setup.",
};

export default function TermsPage() {
  return (
    <main className={styles.page}>
      <div className={styles.shell}>
        <BrandHeader />

        <section className={styles.card}>
          <span className={styles.eyebrow}>Terms</span>
          <h1>Terms of Use</h1>
          <p className={styles.updated}>Last updated: September 2026.</p>

          <div className={styles.prose}>
            <h2>What this service is</h2>
            <p>
              Parent Health Agent is a WhatsApp-based setup that helps a family record basic
              health information for a parent. It is a family coordination tool, not a
              medical service.
            </p>

            <h2>No medical advice</h2>
            <p>
              Parent Health Agent does not diagnose conditions, prescribe or adjust
              medication, or give medical advice of any kind — on WhatsApp or anywhere else.
              Always consult a qualified doctor for medical decisions. If a situation seems
              urgent, contact a medical professional or emergency services directly.
            </p>

            <h2>Consent and verification</h2>
            <p>
              Signing up requires consent, and both the parent and the family member who
              registers them must verify their own WhatsApp number before any setup
              conversation begins. Only the phone numbers you provide are used to reach each
              person.
            </p>

            <h2>Accuracy of information</h2>
            <p>
              Information recorded during setup is self-reported by the family and is not
              independently verified for medical accuracy.
            </p>

            <h2>Changes to the service</h2>
            <p>
              This service is under active development. Features described on our website
              reflect what is currently available, and we&apos;ll update this page as that
              changes.
            </p>

            <h2>Contact</h2>
            <p>
              Questions about these terms can be sent through the{" "}
              <a href="/delete-data">data deletion page</a>, which reaches the same team.
            </p>
          </div>
        </section>
      </div>
    </main>
  );
}
