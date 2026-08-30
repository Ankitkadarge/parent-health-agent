"use client";

import { FormEvent, useState } from "react";
import { ApiError, createFamily, FamilyInvite } from "@/lib/api";

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
  const [invites, setInvites] = useState<FamilyInvite[]>([]);
  const [groupCreated, setGroupCreated] = useState(false);

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
      setInvites(result.invites);
      setGroupCreated(result.whatsapp_group_created);
      setStatus("success");
    } catch (err) {
      setStatus("error");
      setErrorMessage(
        err instanceof ApiError ? err.message : "Could not reach the server. Please try again."
      );
    }
  }

  if (status === "success" && familyId) {
    const parentFirstName = form.parentName.split(" ")[0] || "your parent";
    const childInvite = invites.find((invite) => invite.role === "child");
    const parentInvite = invites.find((invite) => invite.role === "parent");

    return (
      <div className="success-state">
        <div className="success-icon">
          <svg width="26" height="26" viewBox="0 0 24 24" fill="none">
            <path
              d="m5 12.5 4.5 4.5L19 7.5"
              stroke="#fff"
              strokeWidth="2.4"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        </div>
        <p className="success-title">You&apos;re on the list</p>
        {groupCreated ? (
          <p className="success-sub">
            We&apos;ve created a WhatsApp group with you and {parentFirstName} — check WhatsApp
            now to get started.
          </p>
        ) : (
          <p className="success-sub">
            We&apos;ve created your family profile. Use the links below on WhatsApp to verify
            yourself and {parentFirstName}.
          </p>
        )}

        <div className="invite-links">
          {childInvite && (
            <a href={childInvite.invite_url} target="_blank" rel="noreferrer">
              Your verification link
            </a>
          )}
          {parentInvite && (
            <a href={parentInvite.invite_url} target="_blank" rel="noreferrer">
              {parentFirstName}&apos;s verification link
            </a>
          )}
        </div>

        <p className="reference-id">Reference ID: {familyId}</p>
      </div>
    );
  }

  return (
    <form className="form" onSubmit={handleSubmit}>
      <fieldset className="form-fieldset">
        <legend className="form-legend">Your details</legend>
        <div className="form-row">
          <input
            id="childName"
            required
            value={form.childName}
            onChange={(e) => updateField("childName", e.target.value)}
            placeholder="Your name"
            aria-label="Your name"
            disabled={status === "submitting"}
          />
          <input
            id="childPhone"
            required
            type="tel"
            value={form.childPhone}
            onChange={(e) => updateField("childPhone", e.target.value)}
            placeholder="Your WhatsApp number"
            aria-label="Your WhatsApp number"
            disabled={status === "submitting"}
          />
        </div>
      </fieldset>

      <fieldset className="form-fieldset">
        <legend className="form-legend">Your parent&apos;s details</legend>
        <div className="form-row">
          <input
            id="parentName"
            required
            value={form.parentName}
            onChange={(e) => updateField("parentName", e.target.value)}
            placeholder="Parent's name"
            aria-label="Parent's name"
            disabled={status === "submitting"}
          />
          <input
            id="parentPhone"
            required
            type="tel"
            value={form.parentPhone}
            onChange={(e) => updateField("parentPhone", e.target.value)}
            placeholder="Parent's WhatsApp number"
            aria-label="Parent's WhatsApp number"
            disabled={status === "submitting"}
          />
        </div>
        <select
          id="parentLanguage"
          value={form.parentLanguage}
          onChange={(e) => updateField("parentLanguage", e.target.value)}
          aria-label="Parent's preferred language"
          disabled={status === "submitting"}
        >
          {LANGUAGE_OPTIONS.map((lang) => (
            <option key={lang} value={lang}>
              {lang}
            </option>
          ))}
        </select>
      </fieldset>

      <label className="form-check">
        <input
          type="checkbox"
          checked={form.consent}
          onChange={(e) => updateField("consent", e.target.checked)}
          required
          disabled={status === "submitting"}
        />
        <span>
          I confirm my parent has agreed to receive WhatsApp messages from this service about
          their health check-ins.
        </span>
      </label>

      {status === "error" && errorMessage && <div className="error-msg">{errorMessage}</div>}

      <button type="submit" disabled={status === "submitting"}>
        {status === "submitting" ? "Submitting…" : "Get started"}
      </button>
    </form>
  );
}
