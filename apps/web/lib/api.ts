export type FamilyCreatePayload = {
  child_name: string;
  child_phone: string;
  parent_name: string;
  parent_phone: string;
  parent_preferred_language: string;
  consent: boolean;
  website?: string;
};

export type FamilyInvite = {
  role: "child" | "parent";
  token: string;
  invite_url: string;
  expires_at: string;
};

export type FamilyCreateResponse = {
  family_id: string;
  invites: FamilyInvite[];
  whatsapp_group_created: boolean;
};

export class ApiError extends Error {
  status: number;
  requestId: string | null;

  constructor(
    message: string,
    status = 0,
    requestId: string | null = null,
  ) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.requestId = requestId;
  }
}

function detailFromBody(body: unknown): string | null {
  if (!body || typeof body !== "object") {
    return null;
  }

  const detail = (body as { detail?: unknown }).detail;
  if (typeof detail === "string") {
    return detail;
  }

  if (Array.isArray(detail)) {
    const messages = detail
      .map((item) => {
        if (!item || typeof item !== "object") {
          return null;
        }
        const message = (item as { msg?: unknown }).msg;
        return typeof message === "string" ? message : null;
      })
      .filter((message): message is string => Boolean(message));

    return messages.length > 0 ? messages.join(" ") : null;
  }

  return null;
}

function isFamilyInvite(value: unknown): value is FamilyInvite {
  if (!value || typeof value !== "object") {
    return false;
  }

  const invite = value as Partial<FamilyInvite>;
  return (
    (invite.role === "child" || invite.role === "parent") &&
    typeof invite.token === "string" &&
    typeof invite.invite_url === "string" &&
    typeof invite.expires_at === "string"
  );
}

function parseFamilyResponse(body: unknown): FamilyCreateResponse {
  if (!body || typeof body !== "object") {
    throw new ApiError("The server returned an invalid response.", 502);
  }

  const record = body as Record<string, unknown>;
  const invites = record.invites;

  if (
    typeof record.family_id !== "string" ||
    !Array.isArray(invites) ||
    !invites.every(isFamilyInvite)
  ) {
    throw new ApiError("The server returned an invalid response.", 502);
  }

  return {
    family_id: record.family_id,
    invites,
    whatsapp_group_created: record.whatsapp_group_created === true,
  };
}

export async function createFamily(
  payload: FamilyCreatePayload,
): Promise<FamilyCreateResponse> {
  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort(), 45_000);

  try {
    const response = await fetch("/api/families", {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
      cache: "no-store",
      signal: controller.signal,
    });

    const requestId = response.headers.get("x-request-id");
    const raw = await response.text();
    let body: unknown = null;

    if (raw) {
      try {
        body = JSON.parse(raw);
      } catch {
        body = null;
      }
    }

    if (!response.ok) {
      throw new ApiError(
        detailFromBody(body) ??
          "Something went wrong. Please check your details and try again.",
        response.status,
        requestId,
      );
    }

    return parseFamilyResponse(body);
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }

    if (error instanceof Error && error.name === "AbortError") {
      throw new ApiError(
        "The server is taking too long to respond. Please try again.",
        504,
      );
    }

    throw new ApiError(
      "Could not reach the server. Please check your connection and try again.",
      0,
    );
  } finally {
    window.clearTimeout(timeoutId);
  }
}
