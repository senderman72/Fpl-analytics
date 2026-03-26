/**
 * Generic HTTP client for the FPL Analytics API.
 *
 * All API calls go through this module. Components never call fetch directly.
 * Server-side (Astro SSR) calls hit the FastAPI backend directly.
 * Client-side (SolidJS islands) calls go through Astro API route proxies.
 */

const SERVER_API_URL = import.meta.env.API_URL || 'http://localhost:8000';
const CLIENT_API_PREFIX = '/api';

function getBaseUrl(): string {
  // Server-side: call FastAPI directly
  // Client-side: go through Astro API proxy routes
  return typeof window === 'undefined' ? SERVER_API_URL : CLIENT_API_PREFIX;
}

interface APIResponse<T> {
  data: T;
  meta: Record<string, unknown>;
}

export async function get<T>(
  path: string,
  params?: Record<string, string | number | boolean | undefined>,
): Promise<T> {
  const base = getBaseUrl();
  const url = new URL(`${base}${path}`, 'http://localhost');

  if (params) {
    for (const [key, value] of Object.entries(params)) {
      if (value !== undefined) {
        url.searchParams.set(key, String(value));
      }
    }
  }

  // Use just pathname + search when calling relative (client-side)
  const fetchUrl = typeof window === 'undefined'
    ? url.toString()
    : `${url.pathname}${url.search}`;

  const res = await fetch(fetchUrl);
  if (!res.ok) {
    throw new Error(`API ${res.status}: ${res.statusText}`);
  }

  const json: APIResponse<T> = await res.json();
  return json.data;
}

export async function post<T>(
  path: string,
  body?: Record<string, unknown>,
): Promise<T> {
  const base = getBaseUrl();
  const url = typeof window === 'undefined'
    ? `${base}${path}`
    : `${CLIENT_API_PREFIX}${path}`;

  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) {
    throw new Error(`API ${res.status}: ${res.statusText}`);
  }

  const json: APIResponse<T> = await res.json();
  return json.data;
}
