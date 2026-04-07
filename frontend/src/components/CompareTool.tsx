import { createSignal, createEffect, createMemo, For, Show } from 'solid-js';
import CompareRadar from './CompareRadar';
import { comparePlayers } from '../api/compare';
import { POSITIONS, POSITION_COLORS, formatCost } from '../lib/types';
import type { PlayerComparison, PlayerIdName } from '../lib/types';

interface Props {
  allPlayers: string; // JSON-serialized PlayerIdName[]
  initialIds?: string; // comma-separated, from URL
}

interface StatRow {
  label: string;
  key: string;
  format: (v: PlayerComparison) => string;
  getValue: (v: PlayerComparison) => number;
  higherIsBetter: boolean;
}

const STAT_ROWS: StatRow[] = [
  { label: 'Price', key: 'now_cost', format: (p) => formatCost(p.now_cost), getValue: (p) => -p.now_cost, higherIsBetter: true },
  { label: 'Form Points', key: 'form_points', format: (p) => String(p.form_points ?? '-'), getValue: (p) => p.form_points ?? 0, higherIsBetter: true },
  { label: 'Pts/Game', key: 'pts_per_game', format: (p) => p.pts_per_game ?? '-', getValue: (p) => parseFloat(p.pts_per_game || '0'), higherIsBetter: true },
  { label: 'xGI/90', key: 'xgi_per_90', format: (p) => p.xgi_per_90 ?? '-', getValue: (p) => parseFloat(p.xgi_per_90 || '0'), higherIsBetter: true },
  { label: 'Minutes %', key: 'minutes_pct', format: (p) => p.minutes_pct ? `${parseFloat(p.minutes_pct).toFixed(0)}%` : '-', getValue: (p) => parseFloat(p.minutes_pct || '0'), higherIsBetter: true },
  { label: 'BPS Avg', key: 'bps_avg', format: (p) => p.bps_avg ?? '-', getValue: (p) => parseFloat(p.bps_avg || '0'), higherIsBetter: true },
  { label: 'Goals', key: 'goals', format: (p) => String(p.goals ?? '-'), getValue: (p) => p.goals ?? 0, higherIsBetter: true },
  { label: 'Assists', key: 'assists', format: (p) => String(p.assists ?? '-'), getValue: (p) => p.assists ?? 0, higherIsBetter: true },
  { label: 'Clean Sheets', key: 'clean_sheets', format: (p) => String(p.clean_sheets ?? '-'), getValue: (p) => p.clean_sheets ?? 0, higherIsBetter: true },
  { label: 'Season xG', key: 'season_xg', format: (p) => p.season_xg ? parseFloat(p.season_xg).toFixed(1) : '-', getValue: (p) => parseFloat(p.season_xg || '0'), higherIsBetter: true },
  { label: 'Season xA', key: 'season_xa', format: (p) => p.season_xa ? parseFloat(p.season_xa).toFixed(1) : '-', getValue: (p) => parseFloat(p.season_xa || '0'), higherIsBetter: true },
  { label: 'FDR (next 5)', key: 'fdr_next_5', format: (p) => p.fdr_next_5 ?? '-', getValue: (p) => parseFloat(p.fdr_next_5 || '3'), higherIsBetter: false },
  { label: 'Ownership', key: 'selected_by_percent', format: (p) => p.selected_by_percent ? `${p.selected_by_percent}%` : '-', getValue: (p) => parseFloat(p.selected_by_percent || '0'), higherIsBetter: true },
  { label: 'EP Next', key: 'ep_next', format: (p) => p.ep_next ?? '-', getValue: (p) => parseFloat(p.ep_next || '0'), higherIsBetter: true },
];

function bestIdx(players: PlayerComparison[], row: StatRow): number {
  if (players.length === 0) return -1;
  let best = 0;
  let allEqual = true;
  for (let i = 1; i < players.length; i++) {
    const curr = row.getValue(players[i]);
    const prev = row.getValue(players[best]);
    if (curr !== prev) allEqual = false;
    if (row.higherIsBetter ? curr > prev : curr < prev) best = i;
  }
  return allEqual ? -1 : best;
}

export default function CompareTool(props: Props) {
  const allPlayers = createMemo<PlayerIdName[]>(() => {
    try { return JSON.parse(props.allPlayers); }
    catch { return []; }
  });

  const [selectedIds, setSelectedIds] = createSignal<number[]>(
    props.initialIds
      ? props.initialIds.split(',').map(Number).filter(Boolean).slice(0, 5)
      : []
  );
  const [players, setPlayers] = createSignal<PlayerComparison[]>([]);
  const [loading, setLoading] = createSignal(false);
  const [search, setSearch] = createSignal('');
  const [showDropdown, setShowDropdown] = createSignal(false);

  const playerLookup = createMemo(() => {
    const map = new Map<number, PlayerIdName>();
    for (const p of allPlayers()) map.set(p.id, p);
    return map;
  });

  const selectedNames = createMemo(() =>
    selectedIds().map(id => playerLookup().get(id)).filter(Boolean) as PlayerIdName[]
  );

  const filtered = createMemo(() => {
    const q = search().toLowerCase();
    if (!q || q.length < 2) return [];
    const ids = new Set(selectedIds());
    return allPlayers()
      .filter(p => !ids.has(p.id) && (
        p.first_name.toLowerCase().includes(q) ||
        p.second_name.toLowerCase().includes(q)
      ))
      .slice(0, 8);
  });

  // Fetch comparison data when IDs change (guarded against stale responses)
  let fetchVersion = 0;
  createEffect(() => {
    const ids = selectedIds();
    if (ids.length < 2) {
      setPlayers([]);
      return;
    }
    const version = ++fetchVersion;
    setLoading(true);
    comparePlayers(ids)
      .then((result) => {
        if (version === fetchVersion) setPlayers(result);
      })
      .catch(() => {
        if (version === fetchVersion) setPlayers([]);
      })
      .finally(() => {
        if (version === fetchVersion) setLoading(false);
      });
  });

  // Sync URL
  createEffect(() => {
    const ids = selectedIds();
    if (ids.length >= 2) {
      const url = new URL(window.location.href);
      url.searchParams.set('ids', ids.join(','));
      history.replaceState(null, '', url.toString());
    }
  });

  function addPlayer(id: number) {
    if (selectedIds().length >= 5) return;
    setSelectedIds(prev => [...prev, id]);
    setSearch('');
    setShowDropdown(false);
  }

  function removePlayer(id: number) {
    setSelectedIds(prev => prev.filter(x => x !== id));
  }

  return (
    <div>
      {/* Search + selected chips */}
      <div style={{ 'margin-bottom': '1.5rem' }}>
        <div style={{ position: 'relative' }}>
          <input
            type="text"
            placeholder={selectedIds().length >= 5 ? 'Max 5 players' : 'Search players to compare...'}
            value={search()}
            onInput={(e) => { setSearch(e.currentTarget.value); setShowDropdown(true); }}
            onFocus={() => setShowDropdown(true)}
            disabled={selectedIds().length >= 5}
            style={{
              width: '100%',
              padding: '0.75rem 1rem',
              background: '#16213e',
              border: '1px solid rgba(107,114,128,0.3)',
              'border-radius': '0.5rem',
              color: 'white',
              'font-size': '0.875rem',
              outline: 'none',
            }}
          />
          <Show when={showDropdown() && filtered().length > 0}>
            <div style={{
              position: 'absolute',
              top: '100%',
              left: '0',
              right: '0',
              background: '#1a1a2e',
              border: '1px solid rgba(107,114,128,0.3)',
              'border-radius': '0 0 0.5rem 0.5rem',
              'max-height': '300px',
              'overflow-y': 'auto',
              'z-index': '50',
            }}>
              <For each={filtered()}>
                {(p) => (
                  <button
                    onClick={() => addPlayer(p.id)}
                    style={{
                      display: 'block',
                      width: '100%',
                      padding: '0.5rem 1rem',
                      'text-align': 'left',
                      color: 'white',
                      background: 'transparent',
                      border: 'none',
                      cursor: 'pointer',
                      'font-size': '0.875rem',
                    }}
                    onMouseOver={(e) => { e.currentTarget.style.background = 'rgba(255,255,255,0.05)'; }}
                    onMouseOut={(e) => { e.currentTarget.style.background = 'transparent'; }}
                  >
                    {p.first_name} {p.second_name}
                  </button>
                )}
              </For>
            </div>
          </Show>
        </div>

        {/* Selected player chips — rendered from local state, not async API */}
        <Show when={selectedNames().length > 0}>
          <div style={{ display: 'flex', gap: '0.5rem', 'flex-wrap': 'wrap', 'margin-top': '0.75rem' }}>
            <For each={selectedNames()}>
              {(p) => (
                <span style={{
                  display: 'inline-flex',
                  'align-items': 'center',
                  gap: '0.5rem',
                  padding: '0.25rem 0.75rem',
                  background: 'rgba(255,255,255,0.08)',
                  'border-radius': '9999px',
                  'font-size': '0.8rem',
                  color: 'white',
                }}>
                  {p.first_name} {p.second_name}
                  <button
                    onClick={() => removePlayer(p.id)}
                    aria-label={`Remove ${p.first_name} ${p.second_name}`}
                    style={{ color: '#ef4444', background: 'none', border: 'none', cursor: 'pointer', 'font-size': '1rem', 'line-height': '1' }}
                  >&times;</button>
                </span>
              )}
            </For>
          </div>
        </Show>
      </div>

      <Show when={loading()}>
        <div style={{ 'text-align': 'center', color: '#9ca3af', padding: '2rem' }}>Loading comparison...</div>
      </Show>

      <Show when={!loading() && selectedIds().length < 2}>
        <div style={{ 'text-align': 'center', color: '#9ca3af', padding: '3rem 1rem' }}>
          <p style={{ 'font-size': '1.1rem', 'margin-bottom': '0.5rem' }}>Select 2-5 players to compare</p>
          <p style={{ 'font-size': '0.8rem' }}>Search by name above to add players</p>
        </div>
      </Show>

      <Show when={!loading() && players().length >= 2}>
        {/* Radar chart */}
        <div style={{
          background: 'rgba(22,33,62,0.5)',
          'border-radius': '0.75rem',
          padding: '1rem',
          'margin-bottom': '1.5rem',
        }}>
          <CompareRadar players={players()} />
        </div>

        {/* Stat table */}
        <div style={{ 'overflow-x': 'auto' }}>
          <table style={{ width: '100%', 'font-size': '0.875rem', 'border-collapse': 'collapse' }}>
            <thead>
              <tr style={{ 'border-bottom': '1px solid rgba(107,114,128,0.3)' }}>
                <th style={{ padding: '0.625rem 0.75rem', 'text-align': 'left', color: '#9ca3af', 'font-weight': '500' }}>Stat</th>
                <For each={players()}>
                  {(p) => (
                    <th style={{ padding: '0.625rem 0.75rem', 'text-align': 'center', 'min-width': '110px' }}>
                      <div style={{ display: 'flex', 'flex-direction': 'column', 'align-items': 'center', gap: '0.25rem' }}>
                        <img src={p.shirt_url || ''} alt="" style={{ width: '32px', height: '32px', 'object-fit': 'contain' }} />
                        <span style={{ color: 'white', 'font-weight': '600' }}>{p.web_name}</span>
                        <span style={{ color: '#9ca3af', 'font-size': '0.7rem' }}>
                          {p.team_short_name} · <span style={{ color: POSITION_COLORS[p.position] || '#9ca3af' }}>{POSITIONS[p.position]}</span>
                        </span>
                      </div>
                    </th>
                  )}
                </For>
              </tr>
            </thead>
            <tbody>
              <For each={STAT_ROWS}>
                {(row) => {
                  const best = bestIdx(players(), row);
                  return (
                    <tr style={{ 'border-bottom': '1px solid rgba(107,114,128,0.15)' }}>
                      <td style={{ padding: '0.5rem 0.75rem', color: '#9ca3af', 'font-weight': '500' }}>{row.label}</td>
                      <For each={players()}>
                        {(p, i) => (
                          <td style={{
                            padding: '0.5rem 0.75rem',
                            'text-align': 'center',
                            'font-variant-numeric': 'tabular-nums',
                            color: i() === best ? '#00ff87' : 'white',
                            'font-weight': i() === best ? '700' : '400',
                          }}>
                            {row.format(p)}
                          </td>
                        )}
                      </For>
                    </tr>
                  );
                }}
              </For>
            </tbody>
          </table>
        </div>
      </Show>
    </div>
  );
}
