import type { APIRoute } from 'astro';
import { slugify, buildCanonical } from '../lib/seo';
import { getPlayerIds } from '../api/players';

const staticPages = [
  { path: '/', priority: '1.0', changefreq: 'daily' },
  { path: '/players', priority: '0.9', changefreq: 'daily' },
  { path: '/decisions/captain', priority: '0.8', changefreq: 'daily' },
  { path: '/decisions/buy-sell', priority: '0.8', changefreq: 'daily' },
  { path: '/decisions/prices', priority: '0.7', changefreq: 'daily' },
  { path: '/predictions', priority: '0.8', changefreq: 'daily' },
  { path: '/fixtures', priority: '0.6', changefreq: 'weekly' },
  { path: '/decisions/chips', priority: '0.6', changefreq: 'weekly' },
  { path: '/live', priority: '0.5', changefreq: 'hourly' },
];

function escapeXml(s: string): string {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

export const GET: APIRoute = async () => {
  let playerEntries = '';

  try {
    const players = await getPlayerIds();
    playerEntries = players
      .map((p) => {
        const slug = slugify(p.id, p.first_name, p.second_name);
        const url = escapeXml(buildCanonical(`/players/${slug}`));
        return `  <url><loc>${url}</loc><changefreq>weekly</changefreq><priority>0.7</priority></url>`;
      })
      .join('\n');
  } catch {
    // Backend unavailable — emit static pages only
  }

  const staticEntries = staticPages
    .map(
      (p) =>
        `  <url><loc>${escapeXml(buildCanonical(p.path))}</loc><changefreq>${p.changefreq}</changefreq><priority>${p.priority}</priority></url>`,
    )
    .join('\n');

  const xml = `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${staticEntries}
${playerEntries}
</urlset>`;

  return new Response(xml.trim(), {
    headers: { 'Content-Type': 'application/xml' },
  });
};
