import { createSignal, createResource, For, Show } from 'solid-js';
import { getTransferSuggestions } from '../api/my-team';
import { formatCost, fdrColor } from '../lib/types';
import type { TransferPlan, TransferSuggestion } from '../lib/types';

interface Props {
  managerId: number;
}

function FixtureStrip(props: { fixtures: { opponent: string; difficulty: number; is_home: boolean }[] }) {
  return (
    <div style={{ display: 'flex', gap: '2px' }}>
      <For each={props.fixtures.slice(0, 5)}>
        {(f) => (
          <span style={{
            'font-size': '0.6rem',
            padding: '1px 3px',
            'border-radius': '2px',
            background: fdrColor(f.difficulty),
            color: f.difficulty <= 2 ? '#000' : '#fff',
            'font-weight': '600',
            'white-space': 'nowrap',
          }}>
            {f.opponent}{f.is_home ? '(H)' : '(A)'}
          </span>
        )}
      </For>
    </div>
  );
}

function SuggestionCard(props: { s: TransferSuggestion; idx: number; freeTransfers: number }) {
  const [showWhy, setShowWhy] = createSignal(false);
  const isHit = () => props.idx >= props.freeTransfers;

  return (
    <div style={{
      background: 'rgba(22,33,62,0.6)',
      'border-radius': '0.5rem',
      padding: '1rem',
      border: '1px solid rgba(107,114,128,0.2)',
    }}>
      <div style={{ display: 'flex', 'align-items': 'center', gap: '0.75rem', 'margin-bottom': '0.75rem' }}>
        {/* Sell player */}
        <div style={{ flex: '1', 'min-width': '0' }}>
          <div style={{ display: 'flex', 'align-items': 'center', gap: '0.5rem', 'margin-bottom': '0.25rem' }}>
            <img src={props.s.sell_shirt_url || ''} alt="" style={{ width: '28px', height: '28px', 'object-fit': 'contain' }} />
            <div>
              <div style={{ color: '#ef4444', 'font-weight': '600', 'font-size': '0.875rem' }}>{props.s.sell_web_name}</div>
              <div style={{ color: '#9ca3af', 'font-size': '0.7rem' }}>{props.s.sell_team_short} · {props.s.sell_predicted_pts} pts</div>
            </div>
          </div>
          <FixtureStrip fixtures={props.s.sell_fixtures} />
        </div>

        {/* Arrow */}
        <div style={{ color: '#9ca3af', 'font-size': '1.2rem', 'flex-shrink': '0' }}>→</div>

        {/* Buy player */}
        <div style={{ flex: '1', 'min-width': '0' }}>
          <div style={{ display: 'flex', 'align-items': 'center', gap: '0.5rem', 'margin-bottom': '0.25rem' }}>
            <img src={props.s.buy_shirt_url || ''} alt="" style={{ width: '28px', height: '28px', 'object-fit': 'contain' }} />
            <div>
              <div style={{ color: '#00ff87', 'font-weight': '600', 'font-size': '0.875rem' }}>{props.s.buy_web_name}</div>
              <div style={{ color: '#9ca3af', 'font-size': '0.7rem' }}>{props.s.buy_team_short} · {formatCost(props.s.buy_now_cost)} · {props.s.buy_predicted_pts} pts</div>
            </div>
          </div>
          <FixtureStrip fixtures={props.s.buy_fixtures} />
        </div>

        {/* Score badge */}
        <div style={{ 'text-align': 'center', 'flex-shrink': '0' }}>
          <div style={{
            color: '#00ff87',
            'font-weight': '800',
            'font-size': '1.1rem',
            'font-variant-numeric': 'tabular-nums',
          }}>
            +{props.s.points_gain}
          </div>
          <div style={{ color: '#9ca3af', 'font-size': '0.6rem' }}>pts gain</div>
          <Show when={isHit()}>
            <div style={{ color: '#ef4444', 'font-size': '0.65rem', 'font-weight': '600' }}>-4 hit</div>
          </Show>
        </div>
      </div>

      {/* Why button */}
      <button
        onClick={() => setShowWhy(!showWhy())}
        style={{
          color: '#04f5ff',
          background: 'none',
          border: 'none',
          cursor: 'pointer',
          'font-size': '0.75rem',
          padding: '0',
        }}
      >
        {showWhy() ? 'Hide reasoning' : 'Why?'}
      </button>
      <Show when={showWhy()}>
        <div style={{ color: '#9ca3af', 'font-size': '0.75rem', 'margin-top': '0.25rem' }}>
          {props.s.reasoning}
        </div>
      </Show>
    </div>
  );
}

export default function TransferSuggestions(props: Props) {
  const [plan, { loading, error }] = createResource(
    () => props.managerId || null,
    (id) => getTransferSuggestions(id),
  );

  return (
    <div>
      <h3 style={{
        color: 'white',
        'font-weight': '700',
        'font-size': '1rem',
        'margin-bottom': '0.75rem',
        display: 'flex',
        'align-items': 'center',
        gap: '0.5rem',
      }}>
        <span style={{ color: '#04f5ff' }}>⚡</span> Suggested Transfers
      </h3>

      <Show when={loading}>
        <div style={{ color: '#9ca3af', 'font-size': '0.875rem', padding: '1rem', 'text-align': 'center' }}>
          Analysing your squad...
        </div>
      </Show>

      <Show when={error()}>
        <div style={{ color: '#9ca3af', 'font-size': '0.875rem', padding: '1rem', 'text-align': 'center' }}>
          Could not load transfer suggestions.
        </div>
      </Show>

      <Show when={!loading && !error() && plan()}>
        {(() => {
          const p = plan()!;
          return (
            <>
              <Show when={p.suggestions.length === 0}>
                <div style={{
                  background: 'rgba(22,33,62,0.4)',
                  'border-radius': '0.5rem',
                  padding: '1.5rem',
                  'text-align': 'center',
                  color: '#9ca3af',
                  'font-size': '0.875rem',
                }}>
                  Your squad looks strong — no clear upgrades found.
                </div>
              </Show>
              <div style={{ display: 'flex', 'flex-direction': 'column', gap: '0.75rem' }}>
                <For each={p.suggestions.slice(0, 3)}>
                  {(s, i) => (
                    <SuggestionCard s={s} idx={i()} freeTransfers={p.free_transfers} />
                  )}
                </For>
              </div>
              <Show when={p.suggestions.length > 3}>
                <details style={{ 'margin-top': '0.5rem' }}>
                  <summary style={{
                    color: '#04f5ff',
                    'font-size': '0.8rem',
                    cursor: 'pointer',
                    'text-align': 'center',
                    'list-style': 'none',
                  }}>
                    See {p.suggestions.length - 3} more suggestions
                  </summary>
                  <div style={{ display: 'flex', 'flex-direction': 'column', gap: '0.75rem', 'margin-top': '0.5rem' }}>
                    <For each={p.suggestions.slice(3)}>
                      {(s, i) => (
                        <SuggestionCard s={s} idx={i() + 3} freeTransfers={p.free_transfers} />
                      )}
                    </For>
                  </div>
                </details>
              </Show>
            </>
          );
        })()}
      </Show>
    </div>
  );
}
