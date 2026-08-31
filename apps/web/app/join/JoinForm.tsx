"use client";

import { FormEvent, useState } from "react";

import styles from "./join.module.css";

type JoinResponse = {
  family_id: string;
  member_id: string;
  role: "child" | "parent";
  verified_at: string;
  family_status: "pending_verification" | "onboarding" | "active";
};

type JoinFormProps = {
  token: string;
};

type SubmitState = "idle" | "submitting" | "success" | "error";

const STATUS_MESSAGES: Record<number, string> = {
  400: "Please enter your WhatsApp number.",
  403: "This invitation belongs to a different WhatsApp number.",
  404: "This verification link is invalid.",
  409: "This verification link has already been used.",
  410: "This verification link has expired. Ask the family organiser for a new link.",
  422: "Please enter a valid WhatsApp number, including the country code when needed.",
  502: "The verification service is temporarily unavailable. Please try again.",
  504: "The verification service took too long to respond. Please try again.",
};

function getDetail(body: unknown): string | null {
  if (!body || typeof body !== "object" || !("detail" in body)) {
    return null;
  }

  const detail = (body as { detail?: unknown }).detail;
  return typeof detail === "string" ? detail : null;
}

export default function JoinForm({ token }: JoinFormProps) {
  const [phone, setPhone] = useState("");
  const [state, setState] = useState<SubmitState>("idle");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [result, setResult] = useState<JoinResponse | null>(null);

  const missingToken = token.trim().length === 0;

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (missingToken) {
      setState("error");
      setErrorMessage("This verification link is missing its invitation token.");
      return;
    }

    setState("submitting");
    setErrorMessage(null);

    try {
      const response = await fetch("/api/whatsapp/join", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token, phone }),
      });

      const body: unknown = await response.json().catch(() => null);

      if (!response.ok) {
        throw new Error(
          getDetail(body) ?? STATUS_MESSAGES[response.status] ??
            "We could not verify this invitation. Please try again."
        );
      }

      if (!body || typeof body !== "object" || !("family_id" in body)) {
        throw new Error("The verification service returned an unexpected response.");
      }

      setResult(body as JoinResponse);
      setState("success");
      window.history.replaceState({}, "", "/join");
    } catch (error) {
      setState("error");
      setErrorMessage(
        error instanceof Error
          ? error.message
          : "We could not verify this invitation. Please try again."
      );
    }
  }

  if (state === "success" && result) {
    const waitingForOtherMember = result.family_status === "pending_verification";

    return (
      <div className={styles.success} role="status">
        <span className={styles.successIcon} aria-hidden="true">
          ✓
        </span>
        <div>
          <h2>Your number is verified</h2>
          <p>
            {waitingForOtherMember
              ? "The other family member still needs to use their own verification link."
              : "Both family members are verified. Your family can now begin onboarding."}
          </p>
          <p className={styles.reference}>Family reference: {result.family_id}</p>
        </div>
      </div>
    );
  }

  return (
    <form className={styles.form} onSubmit={handleSubmit}>
      <label htmlFor="phone">Your WhatsApp number</label>
      <input
        id="phone"
        name="phone"
        type="tel"
        inputMode="tel"
        autoComplete="tel"
        placeholder="e.g. +91 98765 43210"
        value={phone}
        onChange={(event) => setPhone(event.target.value)}
        disabled={state === "submitting" || missingToken}
        required
      />

      {missingToken && (
        <div className={styles.error} role="alert">
          This verification link is incomplete. Open the original link again from the
          signup confirmation.
        </div>
      )}

      {state === "error" && errorMessage && !missingToken && (
        <div className={styles.error} role="alert">
          {errorMessage}
        </div>
      )}

      <button type="submit" disabled={state === "submitting" || missingToken}>
        {state === "submitting" ? "Verifying…" : "Verify my number"}
      </button>

      <p className={styles.help}>
        Use the exact number entered during signup. Indian numbers without a country code
        are interpreted as +91 by the backend.
      </p>
    </form>
  );
}
