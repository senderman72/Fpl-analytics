import { defineMiddleware } from 'astro:middleware';

export const onRequest = defineMiddleware(async (_context, next) => {
  const response = await next();

  const isHtml = response.headers.get('content-type')?.includes('text/html');
  const isApi = _context.url.pathname.startsWith('/api/');

  // Security headers on all responses
  response.headers.set('X-Frame-Options', 'SAMEORIGIN');
  response.headers.set('X-Content-Type-Options', 'nosniff');
  response.headers.set('Referrer-Policy', 'strict-origin-when-cross-origin');
  response.headers.set(
    'Permissions-Policy',
    'geolocation=(), microphone=(), camera=()',
  );

  // CSP on HTML pages only
  if (isHtml) {
    response.headers.set(
      'Content-Security-Policy',
      [
        "default-src 'self'",
        "script-src 'self' 'unsafe-inline' https://www.googletagmanager.com",
        "img-src 'self' data: https://fantasy.premierleague.com https://resources.premierleague.com",
        "connect-src 'self' https://www.google-analytics.com",
        "style-src 'self' 'unsafe-inline'",
      ].join('; '),
    );
  }

  // Cache headers on SSR HTML pages (not API routes)
  if (isHtml && !isApi) {
    response.headers.set(
      'Cache-Control',
      'public, s-maxage=3600, stale-while-revalidate=86400',
    );
  }

  return response;
});
