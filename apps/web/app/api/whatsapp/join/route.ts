import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

const rawApiBaseUrl =
  process.env.API_BASE_URL ?? process.env.NEXT_PUBLIC_API_BASE_URL ?? "";
const API_BASE_URL = rawApiBaseUrl.replace(/\/$/, "");

function errorResponse(detail: string, status: number) {
  return NextResponse.json({ detail }, { status });
}

export async function POST(request: Request) {
  let body: unknown;

  try {
    body = await request.json();
  } catch {
    return errorResponse("Request body must be valid JSON.", 400);
  }

  if (!body || typeof body !== "object") {
    return errorResponse("Request body must be an object.", 400);
  }

  const record = body as Record<string, unknown>;
  const token = typeof record.token === "string" ? record.token.trim() : "";
  const phone = typeof record.phone === "string" ? record.phone.trim() : "";

  if (!token || !phone) {
    return errorResponse("Both invitation token and phone number are required.", 400);
  }

  if (!API_BASE_URL) {
    return errorResponse("Verification service is not configured.", 500);
  }

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 20_000);

  try {
    const upstream = await fetch(`${API_BASE_URL}/whatsapp/join`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ token, phone }),
      cache: "no-store",
      signal: controller.signal,
    });

    const raw = await upstream.text();
    let responseBody: unknown = null;

    if (raw) {
      try {
        responseBody = JSON.parse(raw);
      } catch {
        responseBody = {
          detail: upstream.ok
            ? "Verification succeeded, but the backend returned an unreadable response."
            : "The verification service returned an unreadable error response.",
        };
      }
    }

    if (!responseBody || typeof responseBody !== "object") {
      responseBody = {
        detail: upstream.ok
          ? "Verification succeeded."
          : "The verification service returned an empty error response.",
      };
    }

    return NextResponse.json(responseBody, { status: upstream.status });
  } catch (error) {
    if (error instanceof Error && error.name === "AbortError") {
      return errorResponse("The verification service timed out. Please try again.", 504);
    }

    return errorResponse(
      "Could not reach the verification service. Please try again shortly.",
      502
    );
  } finally {
    clearTimeout(timeoutId);
  }
}
