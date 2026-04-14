import { defineConfig, presetUno, presetWebFonts } from 'unocss';

export default defineConfig({
  presets: [
    presetUno(),
    presetWebFonts({
      fonts: {
        sans: {
          name: 'Inter',
          weights: [400, 600, 700],
          provider: 'google',
        },
        mono: {
          name: 'JetBrains Mono',
          weights: [400],
          provider: 'google',
        },
      },
      inlineFonts: false,
    }),
  ],
  theme: {
    colors: {
      fpl: {
        purple: '#37003c',
        green: '#00ff87',
        cyan: '#04f5ff',
        pink: '#e90052',
        gold: '#ffd700',
        dark: '#1a1a2e',
        card: '#16213e',
        surface: '#0f3460',
      },
    },
    animation: {
      keyframes: {
        pulse_soft: '{ 0%,100% { opacity: 1 } 50% { opacity: 0.6 } }',
      },
      durations: {
        pulse_soft: '2s',
      },
      counts: {
        pulse_soft: 'infinite',
      },
    },
  },
  shortcuts: {
    'card': 'bg-fpl-card rounded-xl border border-gray-700/60 shadow-lg',
    'card-hover': 'card hover:border-gray-600 transition-all duration-150',
    'badge-gk': 'text-xs font-semibold px-2 py-0.5 rounded-full bg-amber-500/15 text-amber-400',
    'badge-def': 'text-xs font-semibold px-2 py-0.5 rounded-full bg-blue-500/15 text-blue-400',
    'badge-mid': 'text-xs font-semibold px-2 py-0.5 rounded-full bg-emerald-500/15 text-emerald-400',
    'badge-fwd': 'text-xs font-semibold px-2 py-0.5 rounded-full bg-red-500/15 text-red-400',
    'stat-value': 'text-2xl font-extrabold text-white leading-none',
    'stat-label': 'text-xs text-gray-400 uppercase tracking-wider',
    'section-title': 'text-lg font-semibold text-white',
    'page-title': 'text-2xl md:text-3xl font-extrabold text-white tracking-tight',
    'link-cyan': 'text-fpl-cyan hover:underline decoration-fpl-cyan/40 underline-offset-2',
  },
});
