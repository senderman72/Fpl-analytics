import { createSignal, For, Show } from 'solid-js';
import type { PredictedLineup, LineupPlayer } from '../lib/types';

const CONF_COLORS = {
  likely: '#10b981',
  rotation: '#f59e0b',
  doubt: '#ef4444',
} as const;

function PlayerDot(props: { player: LineupPlayer }) {
  const color = () => CONF_COLORS[props.player.confidence] || '#6b7280';
  return (
    <div style={{ display: 'flex', 'flex-direction': 'column', 'align-items': 'center', gap: '1px', 'min-width': '0' }}>
      <img
        src={props.player.shirt_url || ''}
        alt=""
        style={{ width: '24px', height: '24px', 'object-fit': 'contain' }}
      />
      <span style={{
        'font-size': '0.5625rem',
        color: color(),
        'font-weight': '600',
        'max-width': '52px',
        overflow: 'hidden',
        'text-overflow': 'ellipsis',
        'white-space': 'nowrap',
        'text-align': 'center',
      }}>
        {props.player.web_name}
      </span>
    </div>
  );
}

function PitchRow(props: { players: LineupPlayer[] }) {
  return (
    <div style={{ display: 'flex', 'justify-content': 'center', gap: '0.25rem' }}>
      <For each={props.players}>
        {(p) => <PlayerDot player={p} />}
      </For>
    </div>
  );
}

export default function LineupCard(props: { lineup: PredictedLineup }) {
  const [expanded, setExpanded] = createSignal(false);
  const l = props.lineup;

  const rows = () => {
    const gk = l.starters.filter(p => p.position === 1);
    const def_ = l.starters.filter(p => p.position === 2);
    const mid = l.starters.filter(p => p.position === 3);
    const fwd = l.starters.filter(p => p.position === 4);
    return [gk, def_, mid, fwd];
  };

  const likelyCount = () => l.starters.filter(p => p.confidence === 'likely').length;
  const doubtCount = () => l.starters.filter(p => p.confidence === 'doubt').length;

  return (
    <div
      style={{
        background: 'rgba(22,33,62,0.6)',
        'border-radius': '0.5rem',
        border: '1px solid rgba(107,114,128,0.2)',
        overflow: 'hidden',
        cursor: 'pointer',
      }}
      onClick={() => setExpanded(!expanded())}
    >
      {/* Header */}
      <div style={{
        display: 'flex',
        'align-items': 'center',
        'justify-content': 'space-between',
        padding: '0.5rem 0.625rem',
        'border-bottom': '1px solid rgba(107,114,128,0.15)',
      }}>
        <div style={{ display: 'flex', 'align-items': 'center', gap: '0.375rem' }}>
          {l.team_badge_url && (
            <img src={l.team_badge_url} alt="" style={{ width: '20px', height: '20px' }} />
          )}
          <span style={{ color: 'white', 'font-weight': '700', 'font-size': '0.75rem' }}>{l.team_short_name}</span>
        </div>
        <div style={{ display: 'flex', 'align-items': 'center', gap: '0.5rem' }}>
          <span style={{ color: '#9ca3af', 'font-size': '0.625rem' }}>{l.formation}</span>
          <span style={{ color: '#10b981', 'font-size': '0.5625rem' }}>{likelyCount()}</span>
          <Show when={doubtCount() > 0}>
            <span style={{ color: '#ef4444', 'font-size': '0.5625rem' }}>{doubtCount()}?</span>
          </Show>
        </div>
      </div>

      {/* Mini pitch */}
      <div style={{
        padding: '0.375rem 0.25rem',
        background: 'linear-gradient(180deg, #1a472a 0%, #2d6a3f 50%, #1a472a 100%)',
        display: 'flex',
        'flex-direction': 'column',
        gap: '0.25rem',
      }}>
        <For each={rows()}>
          {(row) => <PitchRow players={row} />}
        </For>
      </div>

      {/* Expanded: bench + details */}
      <Show when={expanded()}>
        <div style={{ padding: '0.5rem 0.625rem', 'border-top': '1px solid rgba(107,114,128,0.15)' }}>
          <div style={{ color: '#6b7280', 'font-size': '0.5625rem', 'text-transform': 'uppercase', 'margin-bottom': '0.25rem', 'font-weight': '600' }}>
            Bench
          </div>
          <div style={{ display: 'flex', 'flex-wrap': 'wrap', gap: '0.375rem' }}>
            <For each={l.bench.slice(0, 4)}>
              {(p) => (
                <span style={{
                  'font-size': '0.625rem',
                  color: CONF_COLORS[p.confidence] || '#6b7280',
                  padding: '1px 4px',
                  background: 'rgba(255,255,255,0.05)',
                  'border-radius': '3px',
                }}>
                  {p.web_name}
                </span>
              )}
            </For>
          </div>
          {/* Show doubt/news players */}
          {l.starters.filter(p => p.news).length > 0 && (
            <div style={{ 'margin-top': '0.375rem' }}>
              <For each={l.starters.filter(p => p.news)}>
                {(p) => (
                  <div style={{ 'font-size': '0.5625rem', color: '#f59e0b', 'margin-top': '2px' }}>
                    {p.web_name}: {p.news}
                  </div>
                )}
              </For>
            </div>
          )}
        </div>
      </Show>
    </div>
  );
}
