"use client";

import { FormEvent, useState } from "react";
import { ApiError, createFamily, FamilyInvite } from "@/lib/api";
import { phoneFingerprint } from "@/lib/phone";

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
  "Other",
];

type FormState = {
  childName: string;
  childPhone: string;
  parentName: string;
  parentPhone: string;
  parentLanguage: string;
  consent: boolean;
  website: string;
};

const initialState: FormState = {
  childName: "",
  childPhone: "",
  parentName: "",
  parentPhone: "",
  parentLanguage: "English",
  consent: false,
  website: "",
};


export default function FamilySignupForm() {
  const [form, setForm] = useState<FormState>(initialState);
  const [status, setStatus] = useState<
    "idle" | "submitting" | "success" | "error"
  >("idle");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [errorRequestId, setErrorRequestId] = useState<string | null>(null);
  const [familyId, setFamilyId] = useState<string | null>(null);
  const [invites, setInvites] = useState<FamilyInvite[]>([]);
  const [groupCreated, setGroupCreated] = useState(false);

  function updateField<K extends keyof FormState>(
    field: K,
    value: FormState[K],
  ) {
    setForm((previous) => ({ ...previous, [field]: value }));
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setErrorMessage(null);
    setErrorRequestId(null);

    const childName = form.childName.trim();
    const childPhone = form.childPhone.trim();
    const parentName = form.parentName.trim();
    const parentPhone = form.parentPhone.trim();

    if (
      phoneFingerprint(childPhone) &&
      phoneFingerprint(childPhone) === phoneFingerprint(parentPhone)
    ) {
      setStatus("error");
      setErrorMessage(
        "Your WhatsApp number and your parent's WhatsApp number must be different.",
      );
      return;
    }

    setStatus("submitting");

    try {
      const result = await createFamily({
        child_name: childName,
        child_phone: childPhone,
        parent_name: parentName,
        parent_phone: parentPhone,
        parent_preferred_language: form.parentLanguage,
        consent: form.consent,
        website: form.website,
      });

      setForm((previous) => ({
        ...previous,
        childName,
        childPhone,
        parentName,
        parentPhone,
      }));
      setFamilyId(result.family_id);
      setInvites(result.invites);
      setGroupCreated(result.whatsapp_group_created);
      setStatus("success");
    } catch (error) {
      setStatus("error");

      if (error instanceof ApiError) {
        setErrorMessage(error.message);
        setErrorRequestId(error.requestId);
      } else {
        setErrorMessage(
          "Could not reach the server. Please check your connection and try again.",
        );
      }
    }
  }

  if (status === "success" && familyId) {
    const parentFirstName = form.parentName.split(" ")[0] || "your parent";
    const childInvite = invites.find((invite) => invite.role === "child");
    const parentInvite = invites.find((invite) => invite.role === "parent");

    return (
      <div className="success-state" aria-live="polite">
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
            We&apos;ve created a WhatsApp group with you and {parentFirstName}.
            Check WhatsApp now to get started.
          </p>
        ) : (
          <p className="success-sub">
            We&apos;ve created your family profile. Open each link below to
            verify yourself and {parentFirstName}.
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
            name="childName"
            required
            maxLength={255}
            autoComplete="name"
            value={form.childName}
            onChange={(event) =>
              updateField("childName", event.target.value)
            }
            placeholder="Your name"
            aria-label="Your name"
            disabled={status === "submitting"}
          />
          <input
            id="childPhone"
            name="childPhone"
            required
            type="tel"
            inputMode="tel"
            maxLength={32}
            autoComplete="tel"
            value={form.childPhone}
            onChange={(event) =>
              updateField("childPhone", event.target.value)
            }
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
            name="parentName"
            required
            maxLength={255}
            autoComplete="off"
            value={form.parentName}
            onChange={(event) =>
              updateField("parentName", event.target.value)
            }
            placeholder="Parent's name"
            aria-label="Parent's name"
            disabled={status === "submitting"}
          />
          <input
            id="parentPhone"
            name="parentPhone"
            required
            type="tel"
            inputMode="tel"
            maxLength={32}
            autoComplete="off"
            value={form.parentPhone}
            onChange={(event) =>
              updateField("parentPhone", event.target.value)
            }
            placeholder="Parent's WhatsApp number"
            aria-label="Parent's WhatsApp number"
            disabled={status === "submitting"}
          />
        </div>
        <select
          id="parentLanguage"
          name="parentLanguage"
          value={form.parentLanguage}
          onChange={(event) =>
            updateField("parentLanguage", event.target.value)
          }
          aria-label="Parent's preferred language"
          disabled={status === "submitting"}
        >
          {LANGUAGE_OPTIONS.map((language) => (
            <option key={language} value={language}>
              {language}
            </option>
          ))}
        </select>
      </fieldset>

      <div
        aria-hidden="true"
        style={{
          position: "absolute",
          left: "-10000px",
          width: "1px",
          height: "1px",
          overflow: "hidden",
        }}
      >
        <label htmlFor="website">
          Website
          <input
            id="website"
            name="website"
            type="text"
            tabIndex={-1}
            autoComplete="off"
            value={form.website}
            onChange={(event) =>
              updateField("website", event.target.value)
            }
          />
        </label>
      </div>

      <label className="form-check">
        <input
          type="checkbox"
          checked={form.consent}
          onChange={(event) =>
            updateField("consent", event.target.checked)
          }
          required
          disabled={status === "submitting"}
        />
        <span>
          I confirm my parent has agreed to receive WhatsApp messages from this
          service about their health check-ins.
        </span>
      </label>

      {status === "error" && errorMessage && (
        <div className="error-msg" role="alert" aria-live="polite">
          {errorMessage}
          {errorRequestId && (
            <small style={{ display: "block", marginTop: "6px" }}>
              Support reference: {errorRequestId}
            </small>
          )}
        </div>
      )}

      <button type="submit" disabled={status === "submitting"}>
        {status === "submitting" ? "Submitting…" : "Get started"}
      </button>
    </form>
  );
}
