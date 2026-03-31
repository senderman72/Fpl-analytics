/**
 * Analytics helper — thin wrapper around gtag for custom events.
 *
 * Usage:
 *   import { trackEvent } from '../lib/analytics';
 *   trackEvent('captain_pick_viewed', { player: 'Saka' });
 */

declare global {
  interface Window {
    gtag: (...args: unknown[]) => void;
  }
}

export function trackEvent(
  name: string,
  params?: Record<string, string | number | boolean>,
): void {
  if (typeof window !== 'undefined' && typeof window.gtag === 'function') {
    window.gtag('event', name, params);
  }
}

// Pre-defined event names for consistency
export const events = {
  CAPTAIN_PICK_VIEWED: 'captain_pick_viewed',
  TRANSFER_ADVICE_VIEWED: 'transfer_advice_viewed',
  PREDICTION_VIEWED: 'prediction_viewed',
  PLAYER_PROFILE_VIEWED: 'player_profile_viewed',
  PRICE_CHANGES_VIEWED: 'price_changes_viewed',
  SHARE_CLICKED: 'share_clicked',
  PWA_INSTALLED: 'pwa_installed',
} as const;