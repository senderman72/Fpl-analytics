import { createSignal, onMount, onCleanup, Show } from 'solid-js';
import { trackEvent } from '../lib/analytics';

type Platform = 'android' | 'ios' | 'desktop';

export default function InstallPrompt() {
  const [visible, setVisible] = createSignal(false);
  const [platform, setPlatform] = createSignal<Platform>('desktop');
  const [deferredPrompt, setDeferredPrompt] = createSignal<BeforeInstallPromptEvent | null>(null);

  onMount(() => {
    if (window.matchMedia('(display-mode: standalone)').matches) return;
    if (localStorage.getItem('install_dismissed')) return;
    if (sessionStorage.getItem('install_shown')) return;

    const ua = navigator.userAgent;
    if (/iPhone|iPad|iPod/.test(ua)) {
      setPlatform('ios');
    } else if (/Android/.test(ua)) {
      setPlatform('android');
    }

    setVisible(true);
    sessionStorage.setItem('install_shown', '1');
  });

  // Listen for Chrome/Edge install prompt
  function onBeforeInstall(e: Event) {
    e.preventDefault();
    setDeferredPrompt(e as BeforeInstallPromptEvent);
    setPlatform('android');
    if (!localStorage.getItem('install_dismissed') && !sessionStorage.getItem('install_shown')) {
      setVisible(true);
      sessionStorage.setItem('install_shown', '1');
    }
  }

  function onAppInstalled() {
    trackEvent('pwa_installed');
    setVisible(false);
    setDeferredPrompt(null);
  }

  onMount(() => {
    window.addEventListener('beforeinstallprompt', onBeforeInstall);
    window.addEventListener('appinstalled', onAppInstalled);

    onCleanup(() => {
      window.removeEventListener('beforeinstallprompt', onBeforeInstall);
      window.removeEventListener('appinstalled', onAppInstalled);
    });
  });

  async function handleInstall() {
    const prompt = deferredPrompt();
    if (prompt) {
      await prompt.prompt();
      const result = await prompt.userChoice;
      if (result.outcome === 'accepted') {
        trackEvent('pwa_installed');
      }
      setDeferredPrompt(null);
      setVisible(false);
    }
  }

  function dismiss() {
    localStorage.setItem('install_dismissed', '1');
    setVisible(false);
  }

  return (
    <Show when={visible()}>
      <div
        style={{
          position: 'fixed',
          inset: '0',
          'z-index': '100',
          background: 'rgba(0, 0, 0, 0.5)',
          'backdrop-filter': 'blur(4px)',
          '-webkit-backdrop-filter': 'blur(4px)',
        }}
        onClick={dismiss}
      />
      <div
        style={{
          position: 'fixed',
          bottom: '72px',
          left: '50%',
          transform: 'translateX(-50%)',
          'z-index': '101',
          width: 'calc(100% - 2rem)',
          'max-width': '400px',
        }}
      >
        <div
          style={{
            background: '#1a1a2e',
            border: '1px solid rgba(0, 255, 135, 0.25)',
            'border-radius': '16px',
            padding: '16px',
            'box-shadow': '0 12px 40px rgba(0,0,0,0.5)',
          }}
        >
          {/* Header */}
          <div style={{ display: 'flex', 'align-items': 'center', gap: '10px', 'margin-bottom': '10px' }}>
            <img src="/icons/icon-192.png" alt="" width="36" height="36" style={{ 'border-radius': '8px' }} />
            <div>
              <div style={{ color: '#fff', 'font-weight': '700', 'font-size': '14px' }}>Add FPL Analytics</div>
              <div style={{ color: '#9ca3af', 'font-size': '12px' }}>Install for quick access</div>
            </div>
          </div>

          <Show when={platform() === 'ios'}>
            <p style={{ color: '#d1d5db', 'font-size': '13px', margin: '0 0 12px 0', 'line-height': '1.5' }}>
              Tap{' '}
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#00ff87" stroke-width="2" style={{ display: 'inline', 'vertical-align': 'middle' }}>
                <path stroke-linecap="round" stroke-linejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
              </svg>
              {' '}then <strong style={{ color: '#00ff87' }}>"Add to Home Screen"</strong>
            </p>
          </Show>

          <Show when={platform() === 'android'}>
            <div style={{ display: 'flex', gap: '8px', 'justify-content': 'flex-end' }}>
              <button
                onClick={dismiss}
                style={{
                  background: 'transparent',
                  border: '1px solid rgba(255,255,255,0.15)',
                  color: '#9ca3af',
                  padding: '8px 16px',
                  'border-radius': '8px',
                  'font-size': '13px',
                  cursor: 'pointer',
                }}
              >
                Not now
              </button>
              <button
                onClick={handleInstall}
                style={{
                  background: '#00ff87',
                  border: 'none',
                  color: '#1a1a2e',
                  padding: '8px 16px',
                  'border-radius': '8px',
                  'font-size': '13px',
                  'font-weight': '700',
                  cursor: 'pointer',
                }}
              >
                Install
              </button>
            </div>
          </Show>

          <Show when={platform() === 'ios'}>
            <button
              onClick={dismiss}
              style={{
                background: 'transparent',
                border: 'none',
                color: '#6b7280',
                'font-size': '12px',
                cursor: 'pointer',
                padding: '4px 0',
                width: '100%',
                'text-align': 'right',
              }}
            >
              Dismiss
            </button>
          </Show>
        </div>
      </div>
    </Show>
  );
}

// Type for beforeinstallprompt event (not in standard lib)
interface BeforeInstallPromptEvent extends Event {
  prompt(): Promise<void>;
  userChoice: Promise<{ outcome: 'accepted' | 'dismissed' }>;
}

declare global {
  interface WindowEventMap {
    beforeinstallprompt: BeforeInstallPromptEvent;
  }
}