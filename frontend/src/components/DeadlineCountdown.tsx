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

  return (
    <Show when={time()} fallback={<span class="text-fpl-pink font-bold">DEADLINE PASSED</span>}>
      {(t) => (
        <div class:list={['flex gap-3', urgent() && 'animate-pulse_soft']}>
          <Unit value={t().days} label="DAYS" />
          <Separator />
          <Unit value={t().hours} label="HRS" />
          <Separator />
          <Unit value={t().minutes} label="MIN" />
          <Separator />
          <Unit value={t().seconds} label="SEC" urgent={urgent()} />
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
