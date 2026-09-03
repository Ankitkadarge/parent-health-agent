"use client";

import { useState } from "react";

import styles from "../app/legal.module.css";

const SUPPORT_EMAIL = "support@parent-health-agent.example";

export default function DeleteDataForm() {
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [role, setRole] = useState("");
  const [details, setDetails] = useState("");
  const [submitted, setSubmitted] = useState(false);

  const handleSubmit = (event: React.FormEvent) => {
    event.preventDefault();

    const subject = encodeURIComponent("Data deletion request — Parent Health Agent");
    const body = encodeURIComponent(
      `Name: ${name}\n` +
        `WhatsApp number on the family record: ${phone}\n` +
        `Your role (parent or family member who signed up): ${role}\n\n` +
        `Details:\n${details}\n\n` +
        `I confirm this is my own WhatsApp number, or I am the family member who ` +
        `originally registered this family and can verify it from that same number.`
    );

    window.location.href = `mailto:${SUPPORT_EMAIL}?subject=${subject}&body=${body}`;
    setSubmitted(true);
  };

  return (
    <>
      <form className={styles.form} onSubmit={handleSubmit}>
        <label>
          Your name
          <input required value={name} onChange={(e) => setName(e.target.value)} />
        </label>
        <label>
          WhatsApp number on the family record
          <input
            required
            type="tel"
            placeholder="+91XXXXXXXXXX"
            value={phone}
            onChange={(e) => setPhone(e.target.value)}
          />
        </label>
        <label>
          Your role
          <input
            required
            placeholder="Parent, or the family member who signed up"
            value={role}
            onChange={(e) => setRole(e.target.value)}
          />
        </label>
        <label>
          Anything else we should know
          <textarea value={details} onChange={(e) => setDetails(e.target.value)} />
        </label>
        <button type="submit" className={styles.submit}>
          Send deletion request
        </button>
      </form>
      {submitted && (
        <p className={styles.status}>
          This opens your email app with a pre-filled request to {SUPPORT_EMAIL}. Send it from
          an address you control, and we&apos;ll follow up to verify your WhatsApp number
          before deleting anything.
        </p>
      )}
    </>
  );
}
