"use client";

import { FormEvent, useState } from "react";
import { ApiError, createFamily } from "@/lib/api";

const LANGUAGE_OPTIONS = [
  "English",
  "Hindi",
  "Marathi",
  "Gujarati",
  "Tamil",
  "Telugu",
  "Kannada",
  "Bengali",
  "Punjabi",
];

type FormState = {
  childName: string;
  childPhone: string;
  parentName: string;
  parentPhone: string;
  parentLanguage: string;
  consent: boolean;
};

const initialState: FormState = {
  childName: "",
  childPhone: "",
  parentName: "",
  parentPhone: "",
  parentLanguage: "English",
  consent: false,
};

export default function FamilySignupForm() {
  const [form, setForm] = useState<FormState>(initialState);
  const [status, setStatus] = useState<"idle" | "submitting" | "success" | "error">("idle");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [familyId, setFamilyId] = useState<string | null>(null);

  function updateField<K extends keyof FormState>(field: K, value: FormState[K]) {
    setForm((prev) => ({ ...prev, [field]: value }));
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setStatus("submitting");
    setErrorMessage(null);

    try {
      const result = await createFamily({
        child_name: form.childName,
        child_phone: form.childPhone,
        parent_name: form.parentName,
        parent_phone: form.parentPhone,
        parent_preferred_language: form.parentLanguage,
        consent: form.consent,
      });
      setFamilyId(result.family_id);
      setStatus("success");
    } catch (err) {
      setStatus("error");
      setErrorMessage(
        err instanceof ApiError ? err.message : "Could not reach the server. Please try again."
      );
    }
  }

  if (status === "success" && familyId) {
    return (
      <div className="card success-card">
        <h2>You&apos;re on the list</h2>
        <p>
          We&apos;ve created your family profile. We&apos;ll reach out on WhatsApp to connect
          with {form.parentName.split(" ")[0] || "your parent"} soon.
        </p>
        <p className="family-id">Reference ID: {familyId}</p>
      </div>
    );
  }

  return (
    <form className="card" onSubmit={handleSubmit}>
      <fieldset>
        <legend>Your details</legend>

        <label htmlFor="childName">Your name</label>
        <input
          id="childName"
          required
          value={form.childName}
          onChange={(e) => updateField("childName", e.target.value)}
          placeholder="e.g. Priya Shah"
        />

        <label htmlFor="childPhone">Your WhatsApp number</label>
        <input
          id="childPhone"
          required
          type="tel"
          value={form.childPhone}
          onChange={(e) => updateField("childPhone", e.target.value)}
          placeholder="e.g. +91 98765 43210"
        />
      </fieldset>

      <fieldset>
        <legend>Your parent&apos;s details</legend>

        <label htmlFor="parentName">Parent&apos;s name</label>
        <input
          id="parentName"
          required
          value={form.parentName}
          onChange={(e) => updateField("parentName", e.target.value)}
          placeholder="e.g. Ramesh Shah"
        />

        <label htmlFor="parentPhone">Parent&apos;s WhatsApp number</label>
        <input
          id="parentPhone"
          required
          type="tel"
          value={form.parentPhone}
          onChange={(e) => updateField("parentPhone", e.target.value)}
          placeholder="e.g. +91 98765 00000"
        />

        <label htmlFor="parentLanguage">Parent&apos;s preferred language</label>
        <select
          id="parentLanguage"
          value={form.parentLanguage}
          onChange={(e) => updateField("parentLanguage", e.target.value)}
        >
          {LANGUAGE_OPTIONS.map((lang) => (
            <option key={lang} value={lang}>
              {lang}
            </option>
          ))}
        </select>
      </fieldset>

      <label className="consent-row">
        <input
          type="checkbox"
          checked={form.consent}
          onChange={(e) => updateField("consent", e.target.checked)}
          required
        />
        <span>
          I confirm my parent has agreed to receive WhatsApp messages from this service about
          their health check-ins.
        </span>
      </label>

      {status === "error" && errorMessage && <p className="error-text">{errorMessage}</p>}

      <button type="submit" disabled={status === "submitting"}>
        {status === "submitting" ? "Submitting…" : "Get started"}
      </button>
    </form>
  );
}
