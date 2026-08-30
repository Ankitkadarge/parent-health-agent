export type FamilyCreatePayload = {
  child_name: string;
  child_phone: string;
  parent_name: string;
  parent_phone: string;
  parent_preferred_language: string;
  consent: boolean;
};

export type FamilyCreateResponse = {
  family_id: string;
};

export class ApiError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "ApiError";
  }
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export async function createFamily(
  payload: FamilyCreatePayload
): Promise<FamilyCreateResponse> {
  const response = await fetch(`${API_BASE_URL}/families`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    const detail =
      typeof body?.detail === "string"
        ? body.detail
        : Array.isArray(body?.detail)
          ? body.detail.map((d: { msg: string }) => d.msg).join(" ")
          : "Something went wrong. Please check your details and try again.";
    throw new ApiError(detail);
  }

  return response.json();
}
