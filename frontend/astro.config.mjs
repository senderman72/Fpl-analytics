// @ts-check
import { defineConfig } from 'astro/config';
import solidJs from '@astrojs/solid-js';
import UnoCSS from '@unocss/astro';

import vercel from '@astrojs/vercel';

export default defineConfig({
  output: 'server',
  integrations: [solidJs(), UnoCSS({ injectReset: true })],
  adapter: vercel({
    imageService: true,
  }),
  build: {
    // Inline all CSS into HTML — eliminates render-blocking stylesheet request
    inlineStylesheets: 'always',
  },
  vite: {
    build: {
      assetsInlineLimit: 4096,
    },
  },
});
