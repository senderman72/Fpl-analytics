import { createSignal, createResource, For, Show } from 'solid-js';
import { getPlayers } from '../api/players';
import { POSITIONS, formatCost } from '../lib/types';
import type { PlayerSummary } from '../lib/types';

export default function PlayerTable(props: { initial: PlayerSummary[] }) {
  const [position, setPosition] = createSignal<number | undefined>();
  const [search, setSearch] = createSignal('');
  const [sortBy, setSortBy] = createSignal('form_points');

  const fetchParams = () => ({
    position: position(),
    search: search().length >= 2 ? search() : undefined,
    sort_by: sortBy(),
    limit: 100,
  });

  const [players] = createResource(fetchParams, (p) => getPlayers(p), {
    initialValue: props.initial,
  });

  return (
    <div>
      <div class="flex flex-wrap gap-3 mb-4">
        <input
          type="text"
          placeholder="Search player..."
          class="bg-fpl-card border border-gray-600 rounded px-3 py-1.5 text-sm text-white placeholder-gray-400 w-48"
          onInput={(e) => setSearch(e.currentTarget.value)}
        />
        <div class="flex gap-1">
          <button
            class={`px-3 py-1.5 rounded text-sm ${!position() ? 'bg-fpl-green/20 text-fpl-green' : 'bg-fpl-card text-gray-300'}`}
            onClick={() => setPosition(undefined)}
          >All</button>
          {[1, 2, 3, 4].map((pos) => (
            <button
              class={`px-3 py-1.5 rounded text-sm ${position() === pos ? 'bg-fpl-green/20 text-fpl-green' : 'bg-fpl-card text-gray-300'}`}
              onClick={() => setPosition(pos)}
            >{POSITIONS[pos]}</button>
          ))}
        </div>
        <select
          class="bg-fpl-card border border-gray-600 rounded px-3 py-1.5 text-sm text-white"
          onChange={(e) => setSortBy(e.currentTarget.value)}
        >
          <option value="form_points">Form Points</option>
          <option value="xgi_per_90">xGI/90</option>
          <option value="pts_per_game">Pts/Game</option>
          <option value="now_cost">Price</option>
          <option value="minutes_pct">Minutes %</option>
        </select>
      </div>

      <div class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead>
            <tr class="text-left text-gray-400 border-b border-gray-700">
              <th class="py-2 px-2">Player</th>
              <th class="py-2 px-2">Team</th>
              <th class="py-2 px-2">Pos</th>
              <th class="py-2 px-2 text-right">Price</th>
              <th class="py-2 px-2 text-right">Form</th>
              <th class="py-2 px-2 text-right">Pts/G</th>
              <th class="py-2 px-2 text-right">xGI/90</th>
              <th class="py-2 px-2 text-right">Mins %</th>
              <th class="py-2 px-2 text-right">BPS</th>
            </tr>
          </thead>
          <tbody>
            <For each={players()}>
              {(p) => (
                <tr class="border-b border-gray-800 hover:bg-fpl-card/50 transition-colors">
                  <td class="py-2 px-2">
                    <a href={`/players/${p.id}`} class="text-fpl-cyan hover:underline font-medium">{p.web_name}</a>
                    <Show when={p.is_penalty_taker}><span class="ml-1 text-xs text-fpl-green" title="Penalty taker">P</span></Show>
                    <Show when={p.is_set_piece_taker}><span class="ml-1 text-xs text-fpl-cyan" title="Set piece taker">S</span></Show>
                  </td>
                  <td class="py-2 px-2 text-gray-400">{p.team_short_name}</td>
                  <td class="py-2 px-2 text-gray-400">{POSITIONS[p.position]}</td>
                  <td class="py-2 px-2 text-right">{formatCost(p.now_cost)}</td>
                  <td class="py-2 px-2 text-right font-medium">{p.form_points ?? '-'}</td>
                  <td class="py-2 px-2 text-right">{p.pts_per_game ?? '-'}</td>
                  <td class="py-2 px-2 text-right">{p.xgi_per_90 ?? '-'}</td>
                  <td class="py-2 px-2 text-right">{p.minutes_pct ? `${Number(p.minutes_pct).toFixed(0)}%` : '-'}</td>
                  <td class="py-2 px-2 text-right">{p.bps_avg ?? '-'}</td>
                </tr>
              )}
            </For>
          </tbody>
        </table>
      </div>
    </div>
  );
}
