import { phoneFingerprint } from "@/lib/phone";
import { jsonError, proxyJsonPost, requestIdFor } from "@/lib/server-api";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";
export const maxDuration = 45;

const MAX_BODY_BYTES = 12_000;

function stringValue(
  record: Record<string, unknown>,
  key: string,
): string {
  return typeof record[key] === "string" ? record[key].trim() : "";
}


export async function POST(request: Request) {
  const requestId = requestIdFor(request);
  const rawBody = await request.text();

  if (new TextEncoder().encode(rawBody).byteLength > MAX_BODY_BYTES) {
    return jsonError("Request body is too large.", 413, requestId);
  }

  let body: unknown;
  try {
    body = JSON.parse(rawBody);
  } catch {
    return jsonError("Request body must be valid JSON.", 400, requestId);
  }

  if (!body || typeof body !== "object" || Array.isArray(body)) {
    return jsonError("Request body must be an object.", 400, requestId);
  }

  const record = body as Record<string, unknown>;

  // Quiet honeypot for automated form spam. Real users never see this field.
  if (stringValue(record, "website")) {
    return jsonError("Unable to submit this form.", 400, requestId);
  }

  const childName = stringValue(record, "child_name");
  const childPhone = stringValue(record, "child_phone");
  const parentName = stringValue(record, "parent_name");
  const parentPhone = stringValue(record, "parent_phone");
  const parentLanguage = stringValue(
    record,
    "parent_preferred_language",
  );
  const consent = record.consent;

  if (
    !childName ||
    !childPhone ||
    !parentName ||
    !parentPhone ||
    !parentLanguage
  ) {
    return jsonError("Please complete every required field.", 400, requestId);
  }

  if (consent !== true) {
    return jsonError(
      "Parent consent is required before signup.",
      400,
      requestId,
    );
  }

  const childFingerprint = phoneFingerprint(childPhone);
  const parentFingerprint = phoneFingerprint(parentPhone);

  if (
    childFingerprint &&
    parentFingerprint &&
    childFingerprint === parentFingerprint
  ) {
    return jsonError(
      "Your WhatsApp number and your parent's WhatsApp number must be different.",
      422,
      requestId,
    );
  }

  return proxyJsonPost(
    "/families",
    {
      child_name: childName,
      child_phone: childPhone,
      parent_name: parentName,
      parent_phone: parentPhone,
      parent_preferred_language: parentLanguage,
      consent: true,
    },
    requestId,
    40_000,
  );
}
