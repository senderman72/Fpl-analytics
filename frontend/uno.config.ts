import { defineConfig, presetUno, presetWebFonts } from 'unocss';

export default defineConfig({
  presets: [
    presetUno(),
    presetWebFonts({
      fonts: {
        sans: 'Inter:400,500,600,700',
        mono: 'JetBrains Mono:400',
      },
    }),
  ],
  theme: {
    colors: {
      fpl: {
        purple: '#37003c',
        green: '#00ff87',
        cyan: '#04f5ff',
        pink: '#e90052',
        dark: '#1a1a2e',
        card: '#16213e',
        surface: '#0f3460',
      },
    },
  },
});
