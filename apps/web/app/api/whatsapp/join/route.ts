import { jsonError, proxyJsonPost, requestIdFor } from "@/lib/server-api";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";
export const maxDuration = 45;

const MAX_BODY_BYTES = 4_000;

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
  const token = typeof record.token === "string" ? record.token.trim() : "";
  const phone = typeof record.phone === "string" ? record.phone.trim() : "";

  if (!token || !phone) {
    return jsonError(
      "Both invitation token and phone number are required.",
      400,
      requestId,
    );
  }

  return proxyJsonPost(
    "/whatsapp/join",
    { token, phone },
    requestId,
    30_000,
  );
}
