import { createSignal, createResource, For, Show } from 'solid-js';
import { getTransferSuggestions } from '../api/my-team';
import { formatCost, fdrColor } from '../lib/types';
import type { TransferSuggestion } from '../lib/types';

interface Props {
  managerId: number;
}

function FixtureStrip(props: { fixtures: { opponent: string; difficulty: number; is_home: boolean }[] }) {
  return (
    <div style={{ display: 'flex', gap: '2px', 'flex-wrap': 'wrap' }}>
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

function PlayerSlot(props: {
  name: string;
  team: string;
  shirtUrl: string | null;
  pts: string;
  cost?: number;
  fixtures: { opponent: string; difficulty: number; is_home: boolean }[];
  color: string;
  label: string;
}) {
  return (
    <div style={{
      display: 'flex',
      'align-items': 'center',
      gap: '0.5rem',
      padding: '0.5rem',
      background: 'rgba(255,255,255,0.03)',
      'border-radius': '0.375rem',
      'min-width': '0',
    }}>
      <img
        src={props.shirtUrl || ''}
        alt=""
        style={{ width: '32px', height: '32px', 'object-fit': 'contain', 'flex-shrink': '0' }}
      />
      <div style={{ flex: '1', 'min-width': '0' }}>
        <div style={{ display: 'flex', 'align-items': 'center', gap: '0.375rem', 'flex-wrap': 'wrap' }}>
          <span style={{
            'font-size': '0.6rem',
            padding: '1px 4px',
            'border-radius': '2px',
            background: props.color === '#ef4444' ? 'rgba(239,68,68,0.15)' : 'rgba(0,255,135,0.15)',
            color: props.color,
            'font-weight': '700',
            'text-transform': 'uppercase',
            'letter-spacing': '0.03em',
          }}>
            {props.label}
          </span>
          <span style={{ color: 'white', 'font-weight': '600', 'font-size': '0.8125rem' }}>{props.name}</span>
          <span style={{ color: '#6b7280', 'font-size': '0.6875rem' }}>{props.team}</span>
        </div>
        <div style={{ display: 'flex', 'align-items': 'center', gap: '0.5rem', 'margin-top': '0.125rem' }}>
          <span style={{ color: '#9ca3af', 'font-size': '0.6875rem' }}>
            {props.pts} pts
            {props.cost != null && ` · ${formatCost(props.cost)}`}
          </span>
        </div>
        <div style={{ 'margin-top': '0.25rem' }}>
          <FixtureStrip fixtures={props.fixtures} />
        </div>
      </div>
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
      padding: '0.75rem',
      border: '1px solid rgba(107,114,128,0.2)',
    }}>
      {/* Score badge — top right */}
      <div style={{
        display: 'flex',
        'justify-content': 'space-between',
        'align-items': 'center',
        'margin-bottom': '0.5rem',
      }}>
        <span style={{ color: '#6b7280', 'font-size': '0.6875rem', 'font-weight': '500' }}>
          Transfer {props.idx + 1}
        </span>
        <div style={{ display: 'flex', 'align-items': 'center', gap: '0.5rem' }}>
          <Show when={isHit()}>
            <span style={{
              color: '#ef4444',
              'font-size': '0.6875rem',
              'font-weight': '600',
              padding: '1px 6px',
              background: 'rgba(239,68,68,0.1)',
              'border-radius': '4px',
            }}>
              -4 hit
            </span>
          </Show>
          <span style={{
            color: '#00ff87',
            'font-weight': '800',
            'font-size': '1rem',
            'font-variant-numeric': 'tabular-nums',
          }}>
            +{props.s.points_gain}
          </span>
          <span style={{ color: '#6b7280', 'font-size': '0.625rem' }}>pts</span>
        </div>
      </div>

      {/* Sell → Buy stacked */}
      <div style={{ display: 'flex', 'flex-direction': 'column', gap: '0.25rem' }}>
        <PlayerSlot
          name={props.s.sell_web_name}
          team={props.s.sell_team_short}
          shirtUrl={props.s.sell_shirt_url}
          pts={props.s.sell_predicted_pts}
          fixtures={props.s.sell_fixtures}
          color="#ef4444"
          label="OUT"
        />
        <PlayerSlot
          name={props.s.buy_web_name}
          team={props.s.buy_team_short}
          shirtUrl={props.s.buy_shirt_url}
          pts={props.s.buy_predicted_pts}
          cost={props.s.buy_now_cost}
          fixtures={props.s.buy_fixtures}
          color="#00ff87"
          label="IN"
        />
      </div>

      {/* Why button */}
      <div style={{ 'margin-top': '0.5rem' }}>
        <button
          onClick={() => setShowWhy(!showWhy())}
          style={{
            color: '#04f5ff',
            background: 'none',
            border: 'none',
            cursor: 'pointer',
            'font-size': '0.6875rem',
            padding: '0',
          }}
        >
          {showWhy() ? 'Hide reasoning' : 'Why this transfer?'}
        </button>
        <Show when={showWhy()}>
          <div style={{ color: '#9ca3af', 'font-size': '0.6875rem', 'margin-top': '0.25rem', 'line-height': '1.4' }}>
            {props.s.reasoning}
          </div>
        </Show>
      </div>
    </div>
  );
}

export default function TransferSuggestions(props: Props) {
  const [plan] = createResource(
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
        Suggested Transfers
      </h3>

      <Show when={plan.loading}>
        <div style={{ color: '#9ca3af', 'font-size': '0.875rem', padding: '1rem', 'text-align': 'center' }}>
          Analysing your squad...
        </div>
      </Show>

      <Show when={plan.error}>
        <div style={{ color: '#9ca3af', 'font-size': '0.875rem', padding: '1rem', 'text-align': 'center' }}>
          Could not load transfer suggestions.
        </div>
      </Show>

      <Show when={!plan.loading && !plan.error && plan()}>
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
