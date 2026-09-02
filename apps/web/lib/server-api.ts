import { randomUUID } from "node:crypto";
import { NextResponse } from "next/server";

const PRODUCTION_API_FALLBACK = "https://parent-health-api.onrender.com";

function configuredApiBaseUrl(): string {
  const candidate =
    process.env.API_BASE_URL ??
    process.env.NEXT_PUBLIC_API_BASE_URL ??
    (process.env.NODE_ENV === "production"
      ? PRODUCTION_API_FALLBACK
      : "http://localhost:8000");

  try {
    const parsed = new URL(candidate);
    if (!["http:", "https:"].includes(parsed.protocol)) {
      return "";
    }
    return parsed.toString().replace(/\/$/, "");
  } catch {
    return "";
  }
}

const API_BASE_URL = configuredApiBaseUrl();

export function requestIdFor(request: Request): string {
  const supplied = request.headers.get("x-request-id")?.trim() ?? "";
  return /^[A-Za-z0-9._-]{1,64}$/.test(supplied) ? supplied : randomUUID();
}

export function jsonError(
  detail: string,
  status: number,
  requestId: string,
): NextResponse {
  return NextResponse.json(
    { detail },
    {
      status,
      headers: {
        "Cache-Control": "no-store",
        "X-Request-ID": requestId,
      },
    },
  );
}

function normalizeUpstreamBody(
  raw: string,
  upstreamOk: boolean,
): Record<string, unknown> {
  if (!raw) {
    return {
      detail: upstreamOk
        ? "The request succeeded."
        : "The service returned an empty error response.",
    };
  }

  try {
    const parsed: unknown = JSON.parse(raw);
    if (parsed && typeof parsed === "object" && !Array.isArray(parsed)) {
      return parsed as Record<string, unknown>;
    }
  } catch {
    // Fall through to the safe, non-upstream-text response below.
  }

  return {
    detail: upstreamOk
      ? "The request succeeded, but the service returned an unreadable response."
      : "The service returned an unreadable error response.",
  };
}

export async function proxyJsonPost(
  path: string,
  payload: Record<string, unknown>,
  requestId: string,
  timeoutMs = 30_000,
): Promise<NextResponse> {
  if (!API_BASE_URL) {
    return jsonError("Backend service is not configured.", 500, requestId);
  }

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const upstream = await fetch(`${API_BASE_URL}${path}`, {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
        "X-Request-ID": requestId,
      },
      body: JSON.stringify(payload),
      cache: "no-store",
      signal: controller.signal,
    });

    const responseBody = normalizeUpstreamBody(
      await upstream.text(),
      upstream.ok,
    );

    return NextResponse.json(responseBody, {
      status: upstream.status,
      headers: {
        "Cache-Control": "no-store",
        "X-Request-ID": requestId,
      },
    });
  } catch (error) {
    if (error instanceof Error && error.name === "AbortError") {
      return jsonError(
        "The backend is taking too long to respond. Please try again.",
        504,
        requestId,
      );
    }

    return jsonError(
      "Could not reach the backend service. Please try again shortly.",
      502,
      requestId,
    );
  } finally {
    clearTimeout(timeoutId);
  }
}
