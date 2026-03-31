import { createSignal, onMount, Show } from 'solid-js';

export default function CookieConsent() {
  const [visible, setVisible] = createSignal(false);

  onMount(() => {
    if (!localStorage.getItem('cookie_consent')) {
      setVisible(true);
    }
  });

  function accept() {
    localStorage.setItem('cookie_consent', 'accepted');
    // Update GA4 consent
    if (typeof window.gtag === 'function') {
      window.gtag('consent', 'update', { analytics_storage: 'granted' });
    }
    setVisible(false);
  }

  function decline() {
    localStorage.setItem('cookie_consent', 'declined');
    setVisible(false);
  }

  return (
    <Show when={visible()}>
      <div
        style={{
          position: 'fixed',
          bottom: '72px',
          left: '50%',
          transform: 'translateX(-50%)',
          'z-index': '45',
          width: 'calc(100% - 2rem)',
          'max-width': '480px',
        }}
      >
        <div
          style={{
            background: '#1a1a2e',
            border: '1px solid rgba(255,255,255,0.1)',
            'border-radius': '12px',
            padding: '16px',
            'box-shadow': '0 8px 32px rgba(0,0,0,0.4)',
          }}
        >
          <p style={{ color: '#d1d5db', 'font-size': '13px', margin: '0 0 12px 0', 'line-height': '1.5' }}>
            We use cookies to understand how you use FPL Analytics and improve the experience.
          </p>
          <div style={{ display: 'flex', gap: '8px', 'justify-content': 'flex-end' }}>
            <button
              onClick={decline}
              style={{
                background: 'transparent',
                border: '1px solid rgba(255,255,255,0.2)',
                color: '#9ca3af',
                padding: '6px 16px',
                'border-radius': '8px',
                'font-size': '13px',
                cursor: 'pointer',
              }}
            >
              Decline
            </button>
            <button
              onClick={accept}
              style={{
                background: '#00ff87',
                border: 'none',
                color: '#1a1a2e',
                padding: '6px 16px',
                'border-radius': '8px',
                'font-size': '13px',
                'font-weight': '600',
                cursor: 'pointer',
              }}
            >
              Accept
            </button>
          </div>
        </div>
      </div>
    </Show>
  );
}

// Extend Window for gtag
declare global {
  interface Window {
    gtag: (...args: unknown[]) => void;
  }
}