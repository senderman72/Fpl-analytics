import { createSignal, onCleanup, Show } from 'solid-js';

interface Props {
  deadline: string;
}

function getTimeLeft(deadline: string) {
  const diff = new Date(deadline).getTime() - Date.now();
  if (diff <= 0) return null;
  const days = Math.floor(diff / 86400000);
  const hours = Math.floor((diff % 86400000) / 3600000);
  const minutes = Math.floor((diff % 3600000) / 60000);
  const seconds = Math.floor((diff % 60000) / 1000);
  return { days, hours, minutes, seconds, total: diff };
}

export default function DeadlineCountdown(props: Props) {
  const [time, setTime] = createSignal(getTimeLeft(props.deadline));

  const interval = setInterval(() => {
    setTime(getTimeLeft(props.deadline));
  }, 1000);

  onCleanup(() => clearInterval(interval));

  const urgent = () => {
    const t = time();
    return t && t.total < 86400000;
  };

  const localDeadline = () =>
    new Date(props.deadline).toLocaleString(undefined, {
      weekday: 'short', day: 'numeric', month: 'short',
      hour: '2-digit', minute: '2-digit',
    });

  return (
    <Show when={time()} fallback={<span class="text-fpl-pink font-bold">DEADLINE PASSED</span>}>
      {(t) => (
        <div>
          <div classList={{'flex gap-3 justify-center': true, 'animate-pulse_soft': !!urgent()}}>
            <Unit value={t().days} label="DAYS" />
            <Separator />
            <Unit value={t().hours} label="HRS" />
            <Separator />
            <Unit value={t().minutes} label="MIN" />
            <Separator />
            <Unit value={t().seconds} label="SEC" urgent={!!urgent()} />
          </div>
          <div class="text-xs text-gray-500 mt-3 text-center">{localDeadline()}</div>
        </div>
      )}
    </Show>
  );
}

function Unit(props: { value: number; label: string; urgent?: boolean }) {
  return (
    <div class="text-center">
      <div class:list={[
        'text-3xl md:text-4xl font-extrabold tabular-nums leading-none',
        props.urgent ? 'text-fpl-pink' : 'text-fpl-green',
      ]}>
        {String(props.value).padStart(2, '0')}
      </div>
      <div class="text-[10px] text-gray-400 mt-1 tracking-widest">{props.label}</div>
    </div>
  );
}

function Separator() {
  return <span class="text-2xl text-gray-600 font-light self-start mt-1">:</span>;
}
