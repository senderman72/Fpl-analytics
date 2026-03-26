/**
 * Catch-all API proxy — forwards all /api/* requests to the FastAPI backend.
 * Keeps API_URL server-side only (never exposed to browser).
 */
import type { APIRoute } from 'astro';

const API_URL = import.meta.env.API_URL || 'http://localhost:8000';

export const GET: APIRoute = async ({ params, url }) => {
  const path = params.path || '';
  const search = url.search;
  const target = `${API_URL}/${path}${search}`;

  const res = await fetch(target);
  const data = await res.text();

  return new Response(data, {
    status: res.status,
    headers: {
      'Content-Type': 'application/json',
      'Cache-Control': 'public, s-maxage=60',
    },
  });
};

export const POST: APIRoute = async ({ params, url, request }) => {
  const path = params.path || '';
  const target = `${API_URL}/${path}${url.search}`;

  const body = await request.text();
  const res = await fetch(target, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body,
  });
  const data = await res.text();

  return new Response(data, {
    status: res.status,
    headers: { 'Content-Type': 'application/json' },
  });
};
