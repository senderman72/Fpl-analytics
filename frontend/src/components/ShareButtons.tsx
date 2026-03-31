import { createSignal } from 'solid-js';
import { trackEvent } from '../lib/analytics';

interface Props {
  url: string;
  text: string;
}

export default function ShareButtons(props: Props) {
  const [copied, setCopied] = createSignal(false);

  const isMobile = () => /iPhone|iPad|iPod|Android/i.test(navigator.userAgent);

  function shareOnX() {
    trackEvent('share_clicked', { method: 'x' });
    const webUrl = `https://x.com/intent/tweet?text=${encodeURIComponent(props.text)}&url=${encodeURIComponent(props.url)}`;
    if (isMobile()) {
      window.open(webUrl, '_blank');
    } else {
      window.open(webUrl, '_blank', 'width=550,height=420');
    }
  }

  function shareOnMessenger() {
    trackEvent('share_clicked', { method: 'messenger' });
    if (isMobile()) {
      window.open(`fb-messenger://share?link=${encodeURIComponent(props.url)}`, '_blank');
    } else {
      window.open(`https://www.facebook.com/dialog/send?link=${encodeURIComponent(props.url)}&redirect_uri=${encodeURIComponent(props.url)}`, '_blank', 'width=550,height=420');
    }
  }

  function shareViaSms() {
    trackEvent('share_clicked', { method: 'sms' });
    window.location.href = `sms:?body=${encodeURIComponent(props.text + ' ' + props.url)}`;
  }

  async function copyLink() {
    trackEvent('share_clicked', { method: 'copy_link' });
    await navigator.clipboard.writeText(props.url);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  const btnClass = 'flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors';

  return (
    <div class="flex flex-wrap items-center gap-2">
      <span class="text-gray-400 text-xs">Share:</span>

      {/* X / Twitter */}
      <button
        onClick={shareOnX}
        class={btnClass}
        style={{ background: 'rgba(255,255,255,0.05)', color: '#e5e7eb' }}
        title="Share on X"
      >
        <svg viewBox="0 0 24 24" class="w-3.5 h-3.5" fill="currentColor">
          <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z" />
        </svg>
        X
      </button>

      {/* Messenger */}
      <button
        onClick={shareOnMessenger}
        class={btnClass}
        style={{ background: 'rgba(0,132,255,0.1)', color: '#0084ff' }}
        title="Share on Messenger"
      >
        <svg viewBox="0 0 24 24" class="w-3.5 h-3.5" fill="currentColor">
          <path d="M12 0C5.373 0 0 4.974 0 11.111c0 3.498 1.744 6.614 4.469 8.654V24l4.088-2.242c1.092.301 2.246.464 3.443.464 6.627 0 12-4.975 12-11.111S18.627 0 12 0zm1.191 14.963l-3.055-3.26-5.963 3.26L10.732 8.2l3.131 3.26 5.886-3.26-6.558 6.763z" />
        </svg>
        Messenger
      </button>

      {/* SMS */}
      <button
        onClick={shareViaSms}
        class={btnClass}
        style={{ background: 'rgba(255,255,255,0.05)', color: '#e5e7eb' }}
        title="Share via SMS"
      >
        <svg viewBox="0 0 24 24" class="w-3.5 h-3.5" fill="none" stroke="currentColor" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
        </svg>
        SMS
      </button>

      {/* Copy link */}
      <button
        onClick={copyLink}
        class={btnClass}
        style={{
          background: copied() ? 'rgba(0,255,135,0.15)' : 'rgba(255,255,255,0.05)',
          color: copied() ? '#00ff87' : '#e5e7eb',
        }}
        title="Copy link"
      >
        <svg viewBox="0 0 24 24" class="w-3.5 h-3.5" fill="none" stroke="currentColor" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
        </svg>
        {copied() ? 'Copied!' : 'Copy'}
      </button>
    </div>
  );
}
