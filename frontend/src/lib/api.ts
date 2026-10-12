/** Minimal typed fetch client for the Uniclyst API.
 *
 * The browser only ever calls relative /api/v1 URLs (Vite proxies them).
 * No external API keys or third-party services are ever touched client-side.
 */

const API_BASE = "/api/v1";

export class ApiError extends Error {
  status: number;
  code: string;

  constructor(status: number, code: string, message: string) {
    super(message);
    this.status = status;
    this.code = code;
  }
}

function getToken(): string | null {
  return localStorage.getItem("uniclyst_token");
}

export function setToken(token: string | null) {
  if (token) localStorage.setItem("uniclyst_token", token);
  else localStorage.removeItem("uniclyst_token");
}

export async function api<T>(
  path: string,
  options: RequestInit & { json?: unknown } = {}
): Promise<T> {
  const headers: Record<string, string> = {
    Accept: "application/json",
    ...(options.headers as Record<string, string>),
  };
  if (options.json !== undefined) headers["Content-Type"] = "application/json";
  const token = getToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const resp = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
    body: options.json !== undefined ? JSON.stringify(options.json) : options.body,
  });

  if (resp.status === 204) return undefined as T;

  let body: any = null;
  try {
    body = await resp.json();
  } catch {
    /* empty body */
  }

  if (!resp.ok) {
    const err = body?.error ?? body?.detail ?? {};
    throw new ApiError(
      resp.status,
      err.code ?? "http_error",
      typeof err === "string" ? err : err.message ?? "Request failed"
    );
  }
  return body as T;
}

export const get = <T>(path: string) => api<T>(path);
export const post = <T>(path: string, json?: unknown) => api<T>(path, { method: "POST", json });
export const patch = <T>(path: string, json?: unknown) => api<T>(path, { method: "PATCH", json });
export const del = <T>(path: string) => api<T>(path, { method: "DELETE" });
