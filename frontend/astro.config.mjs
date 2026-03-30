// @ts-check
import { defineConfig } from 'astro/config';
import solidJs from '@astrojs/solid-js';
import UnoCSS from '@unocss/astro';

import vercel from '@astrojs/vercel';

export default defineConfig({
  output: 'server',
  integrations: [solidJs(), UnoCSS({ injectReset: true })],
  adapter: vercel(),
});