import { createSignal } from 'solid-js';

interface Props {
  url: string;
  text: string;
}

export default function ShareButtons(props: Props) {
  const [copied, setCopied] = createSignal(false);

  function shareOnX() {
    window.open(
      `https://twitter.com/intent/tweet?text=${encodeURIComponent(props.text)}&url=${encodeURIComponent(props.url)}`,
      '_blank',
      'width=550,height=420',
    );
  }

  function shareOnWhatsApp() {
    window.open(
      `https://wa.me/?text=${encodeURIComponent(props.text + ' ' + props.url)}`,
      '_blank',
    );
  }

  function shareOnMessenger() {
    window.open(
      `https://www.facebook.com/dialog/send?link=${encodeURIComponent(props.url)}&app_id=0&redirect_uri=${encodeURIComponent(props.url)}`,
      '_blank',
      'width=550,height=420',
    );
  }

  function shareViaSms() {
    // Uses sms: URI scheme — works on iOS and Android
    window.location.href = `sms:?body=${encodeURIComponent(props.text + ' ' + props.url)}`;
  }

  async function copyLink() {
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

      {/* WhatsApp */}
      <button
        onClick={shareOnWhatsApp}
        class={btnClass}
        style={{ background: 'rgba(37,211,102,0.1)', color: '#25d366' }}
        title="Share on WhatsApp"
      >
        <svg viewBox="0 0 24 24" class="w-3.5 h-3.5" fill="currentColor">
          <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z" />
        </svg>
        WhatsApp
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
