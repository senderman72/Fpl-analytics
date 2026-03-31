import { createSignal, onMount } from 'solid-js';

interface Props {
  date: string;
  weekday?: 'short' | 'long' | 'narrow';
  day?: 'numeric' | '2-digit';
  month?: 'short' | 'long' | 'narrow' | 'numeric' | '2-digit';
  year?: 'numeric' | '2-digit';
  hour?: '2-digit' | 'numeric';
  minute?: '2-digit' | 'numeric';
  class?: string;
}

export default function LocalTime(props: Props) {
  const [text, setText] = createSignal('');

  onMount(() => {
    const options: Intl.DateTimeFormatOptions = {};
    if (props.weekday) options.weekday = props.weekday;
    if (props.day) options.day = props.day;
    if (props.month) options.month = props.month;
    if (props.year) options.year = props.year;
    if (props.hour) options.hour = props.hour;
    if (props.minute) options.minute = props.minute;
    setText(new Date(props.date).toLocaleString(undefined, options));
  });

  return <span class={props.class}>{text()}</span>;
}
