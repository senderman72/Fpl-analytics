import { defineMiddleware } from 'astro:middleware';

export const onRequest = defineMiddleware(async (_context, next) => {
  const response = await next();

  // Add cache headers to SSR HTML pages (not API routes)
  if (
    response.headers.get('content-type')?.includes('text/html') &&
    !_context.url.pathname.startsWith('/api/')
  ) {
    response.headers.set(
      'Cache-Control',
      'public, s-maxage=3600, stale-while-revalidate=86400'
    );
  }

  return response;
});