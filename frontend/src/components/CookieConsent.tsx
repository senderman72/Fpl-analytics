import { createSignal, onMount, Show } from 'solid-js';

type ConsentState = 'undecided' | 'accepted' | 'declined';

export default function CookieConsent() {
  const [state, setState] = createSignal<ConsentState>('undecided');
  const [bannerOpen, setBannerOpen] = createSignal(false);

  onMount(() => {
    const stored = localStorage.getItem('cookie_consent');
    if (stored === 'accepted' || stored === 'declined') {
      setState(stored);
    } else {
      setBannerOpen(true);
    }
  });

  function accept() {
    localStorage.setItem('cookie_consent', 'accepted');
    setState('accepted');
    setBannerOpen(false);
    if (typeof window.gtag === 'function') {
      window.gtag('consent', 'update', { analytics_storage: 'granted' });
    }
  }

  function decline() {
    localStorage.setItem('cookie_consent', 'declined');
    setState('declined');
    setBannerOpen(false);
    if (typeof window.gtag === 'function') {
      window.gtag('consent', 'update', { analytics_storage: 'denied' });
    }
  }

  function toggleBanner() {
    setBannerOpen(prev => !prev);
  }

  const decided = () => state() !== 'undecided';
  const isAccepted = () => state() === 'accepted';

  return (
    <>
      {/* Backdrop overlay — blocks interaction + blur on first visit */}
      <Show when={bannerOpen() && !decided()}>
        <div
          style={{
            position: 'fixed',
            inset: '0',
            'z-index': '44',
            background: 'rgba(0, 0, 0, 0.5)',
            'backdrop-filter': 'blur(4px)',
            '-webkit-backdrop-filter': 'blur(4px)',
          }}
        />
      </Show>

      {/* Full banner */}
      <Show when={bannerOpen()}>
        <div
          style={{
            position: 'fixed',
            bottom: '72px',
            left: '50%',
            transform: 'translateX(-50%)',
            'z-index': '45',
            width: 'calc(100% - 2rem)',
            'max-width': '520px',
          }}
        >
          <div
            style={{
              background: 'linear-gradient(135deg, #1a1a2e 0%, #16213e 100%)',
              border: '1px solid rgba(0, 255, 135, 0.15)',
              'border-radius': '16px',
              padding: '20px',
              'box-shadow': '0 12px 40px rgba(0,0,0,0.5)',
            }}
          >
            {/* Header */}
            <div style={{ display: 'flex', 'align-items': 'center', gap: '8px', 'margin-bottom': '12px' }}>
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#00ff87" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <circle cx="12" cy="12" r="10" />
                <path d="M12 16v-4" />
                <path d="M12 8h.01" />
              </svg>
              <span style={{ color: '#fff', 'font-weight': '700', 'font-size': '15px' }}>Cookie Preferences</span>
            </div>

            {/* Description */}
            <p style={{ color: '#d1d5db', 'font-size': '13px', margin: '0 0 12px 0', 'line-height': '1.6' }}>
              We use analytics cookies to understand which pages and features you use most,
              so we can make FPL Analytics better. We track:
            </p>

            {/* What we track */}
            <ul style={{ color: '#9ca3af', 'font-size': '12px', margin: '0 0 16px 0', 'padding-left': '20px', 'line-height': '1.8' }}>
              <li>Pages visited and time spent</li>
              <li>Features used (captain picks, transfers, predictions)</li>
              <li>Device type and browser (no personal data)</li>
            </ul>

            {/* Current status if revisiting */}
            <Show when={decided()}>
              <p style={{ color: '#6b7280', 'font-size': '12px', margin: '0 0 12px 0', 'font-style': 'italic' }}>
                Currently: analytics {isAccepted() ? 'enabled' : 'disabled'}
              </p>
            </Show>

            {/* Buttons */}
            <div style={{ display: 'flex', gap: '10px', 'justify-content': 'flex-end' }}>
              <button
                onClick={decline}
                style={{
                  background: 'transparent',
                  border: '1px solid rgba(255,255,255,0.15)',
                  color: '#9ca3af',
                  padding: '8px 20px',
                  'border-radius': '8px',
                  'font-size': '13px',
                  cursor: 'pointer',
                  transition: 'all 0.15s',
                }}
              >
                {isAccepted() ? 'Disable' : 'Decline'}
              </button>
              <button
                onClick={accept}
                style={{
                  background: '#00ff87',
                  border: 'none',
                  color: '#1a1a2e',
                  padding: '8px 20px',
                  'border-radius': '8px',
                  'font-size': '13px',
                  'font-weight': '700',
                  cursor: 'pointer',
                  transition: 'all 0.15s',
                }}
              >
                {isAccepted() ? 'Enabled' : 'Accept'}
              </button>
            </div>
          </div>
        </div>
      </Show>

      {/* Small floating button (bottom-right) — shown after user has decided */}
      <Show when={decided() && !bannerOpen()}>
        <button
          onClick={toggleBanner}
          title="Cookie preferences"
          style={{
            position: 'fixed',
            bottom: '80px',
            right: '16px',
            'z-index': '44',
            width: '40px',
            height: '40px',
            'border-radius': '50%',
            background: isAccepted() ? 'rgba(0, 255, 135, 0.15)' : 'rgba(255, 255, 255, 0.08)',
            border: isAccepted() ? '1px solid rgba(0, 255, 135, 0.3)' : '1px solid rgba(255, 255, 255, 0.15)',
            cursor: 'pointer',
            display: 'flex',
            'align-items': 'center',
            'justify-content': 'center',
            transition: 'all 0.15s',
            'box-shadow': '0 4px 12px rgba(0,0,0,0.3)',
          }}
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke={isAccepted() ? '#00ff87' : '#9ca3af'} stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M12 2a10 10 0 1 0 10 10 4 4 0 0 1-5-5 4 4 0 0 1-5-5" />
            <path d="M8.5 8.5v.01" />
            <path d="M16 15.5v.01" />
            <path d="M12 12v.01" />
            <path d="M11 17v.01" />
            <path d="M7 14v.01" />
          </svg>
        </button>
      </Show>
    </>
  );
}

declare global {
  interface Window {
    gtag: (...args: unknown[]) => void;
  }
}