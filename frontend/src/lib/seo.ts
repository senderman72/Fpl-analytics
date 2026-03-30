/** SEO utilities — slugs, canonical URLs, JSON-LD schemas. */

const SITE_URL = import.meta.env.PUBLIC_SITE_URL || 'https://fpl-analytics.vercel.app';

/** Generate a URL-safe slug from player ID + name: "123-erling-haaland" */
export function slugify(id: number, firstName: string, secondName: string): string {
  const name = `${firstName} ${secondName}`
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '') // strip diacritics
    .toLowerCase()
    .replace(/['']/g, '')            // remove apostrophes
    .replace(/[^a-z0-9]+/g, '-')     // non-alphanum → hyphen
    .replace(/-+/g, '-')             // collapse consecutive hyphens
    .replace(/^-|-$/g, '');          // trim leading/trailing hyphens
  return `${id}-${name}`;
}

/** Extract the numeric player ID from a slug like "123-erling-haaland" or plain "123" */
export function playerIdFromSlug(slug: string): number {
  const match = slug.match(/^(\d+)/);
  return match ? parseInt(match[1], 10) : NaN;
}

/** Build a full canonical URL from a pathname. */
export function buildCanonical(path: string): string {
  const clean = path.endsWith('/') && path !== '/' ? path.slice(0, -1) : path;
  return `${SITE_URL}${clean}`;
}

/** JSON-LD: WebSite schema for homepage. */
export function websiteJsonLd() {
  return {
    '@context': 'https://schema.org',
    '@type': 'WebSite',
    name: 'FPL Analytics',
    url: SITE_URL,
    description: 'Data-driven Fantasy Premier League analytics — captain picks, transfer advice, points predictions, and fixture analysis.',
  };
}

/** JSON-LD: WebApplication schema for homepage. */
export function webAppJsonLd() {
  return {
    '@context': 'https://schema.org',
    '@type': 'WebApplication',
    name: 'FPL Analytics',
    url: SITE_URL,
    applicationCategory: 'SportsApplication',
    operatingSystem: 'Any',
    description: 'Free FPL analytics tool with predicted points, captain picks, transfer planner, and chip advisor.',
    offers: {
      '@type': 'Offer',
      price: '0',
      priceCurrency: 'GBP',
    },
  };
}
