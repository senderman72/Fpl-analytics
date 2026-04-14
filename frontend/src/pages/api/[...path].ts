/**
 * Catch-all API proxy — forwards allowed /api/* requests to the FastAPI backend.
 * Keeps API_URL server-side only (never exposed to browser).
 */
import type { APIRoute } from 'astro';

const API_URL = import.meta.env.API_URL || 'http://localhost:8000';

const ALLOWED_PREFIXES = [
  'players', 'predictions', 'decisions', 'gameweeks',
  'fixtures', 'live', 'my-team', 'lineups', 'health',
];

function isAllowedPath(path: string): boolean {
  const clean = path.replace(/\.\./g, '');
  return ALLOWED_PREFIXES.some((p) => clean.startsWith(p));
}

function getCacheControl(path: string): string {
  if (path.startsWith('live/')) {
    return 'public, s-maxage=30, stale-while-revalidate=30';
  }
  if (path.startsWith('my-team/')) {
    return 'private, s-maxage=300';
  }
  return 'public, s-maxage=3600, stale-while-revalidate=86400';
}

export const GET: APIRoute = async ({ params, url }) => {
  const path = params.path || '';
  if (!isAllowedPath(path)) {
    return new Response('Not Found', { status: 404 });
  }
  const target = `${API_URL}/${path}${url.search}`;
  const res = await fetch(target);

  return new Response(res.body, {
    status: res.status,
    headers: {
      'Content-Type': 'application/json',
      'Cache-Control': getCacheControl(path),
    },
  });
};

export const POST: APIRoute = async ({ params, url, request }) => {
  const path = params.path || '';
  if (!isAllowedPath(path)) {
    return new Response('Not Found', { status: 404 });
  }
  const target = `${API_URL}/${path}${url.search}`;
  const body = await request.text();
  const res = await fetch(target, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body,
  });

  return new Response(res.body, {
    status: res.status,
    headers: {
      'Content-Type': 'application/json',
      'Cache-Control': getCacheControl(path),
    },
  });
};
