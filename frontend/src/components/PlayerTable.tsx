import { createSignal, createResource, For, Show } from 'solid-js';
import { getPlayers } from '../api/players';
import { POSITIONS, formatCost } from '../lib/types';
import type { PlayerSummary } from '../lib/types';
import { slugify } from '../lib/seo';

const BADGE_CLASSES: Record<number, string> = {
  1: 'bg-amber-500/15 text-amber-400',
  2: 'bg-blue-500/15 text-blue-400',
  3: 'bg-emerald-500/15 text-emerald-400',
  4: 'bg-red-500/15 text-red-400',
};

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
      {/* Filters */}
      <div class="space-y-3 mb-5">
        {/* Search row */}
        <div class="relative">
          <svg class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          <input
            type="text"
            placeholder="Search player..."
            class="bg-fpl-card border border-gray-600 rounded-lg pl-9 pr-3 py-2.5 text-sm text-white placeholder-gray-500 w-full focus:border-fpl-cyan focus:outline-none transition-colors"
            onInput={(e) => setSearch(e.currentTarget.value)}
          />
        </div>

        {/* Position filters + sort row */}
        <div class="flex flex-wrap items-center gap-2">
          <div class="flex flex-wrap gap-1">
            <button
              class={`px-3 sm:px-4 py-2 rounded-full text-xs font-medium transition-all ${!position() ? 'bg-fpl-green/15 text-fpl-green ring-1 ring-fpl-green/30' : 'bg-fpl-card text-gray-400 hover:text-white'}`}
              onClick={() => setPosition(undefined)}
            >All</button>
            {[1, 2, 3, 4].map((pos) => (
              <button
                class={`px-3 sm:px-4 py-2 rounded-full text-xs font-medium transition-all ${position() === pos ? `${BADGE_CLASSES[pos]} ring-1 ring-current` : 'bg-fpl-card text-gray-400 hover:text-white'}`}
                onClick={() => setPosition(pos)}
              >{POSITIONS[pos]}</button>
            ))}
          </div>

          <select
            class="bg-fpl-card border border-gray-600 rounded-lg px-2 sm:px-3 py-2 text-xs sm:text-sm text-white focus:border-fpl-cyan focus:outline-none"
            onChange={(e) => setSortBy(e.currentTarget.value)}
          >
            <option value="form_points">Sort: Form</option>
            <option value="xgi_per_90">Sort: xGI/90</option>
            <option value="pts_per_game">Sort: Pts/G</option>
            <option value="now_cost">Sort: Price</option>
            <option value="minutes_pct">Sort: Mins %</option>
          </select>

          <Show when={position() || search()}>
            <button
              class="text-xs text-gray-400 hover:text-white transition-colors"
              onClick={() => { setPosition(undefined); setSearch(''); }}
            >Reset</button>
          </Show>
        </div>
      </div>

      {/* Loading skeleton */}
      <Show when={players.loading}>
        <div class="card p-4 space-y-3">
          {Array.from({ length: 8 }, () => (
            <div class="flex gap-4 animate-pulse">
              <div class="h-4 w-28 bg-gray-700/40 rounded" />
              <div class="h-4 w-12 bg-gray-700/40 rounded" />
              <div class="h-4 w-10 bg-gray-700/40 rounded" />
              <div class="h-4 w-16 bg-gray-700/40 rounded" />
              <div class="h-4 w-10 bg-gray-700/40 rounded" />
            </div>
          ))}
        </div>
      </Show>

      {/* Mobile cards */}
      <Show when={!players.loading}>
        <div class="md:hidden space-y-2" data-testid="players-mobile">
          <For each={players()}>
            {(p) => (
              <a href={`/players/${slugify(p.id, p.first_name, p.second_name)}`} class="card p-4 block hover:bg-white/3 transition-colors">
                <div class="flex items-center gap-3 mb-2">
                  <img src={p.shirt_url || ''} alt="" class="w-9 h-9 shrink-0" loading="lazy" />
                  <div class="flex-1 min-w-0">
                    <div class="text-white font-medium truncate">
                      {p.web_name}
                      <span class="text-gray-500 text-xs ml-1">{p.team_short_name}</span>
                      <Show when={p.is_penalty_taker}>
                        <span class="ml-1 text-[11px] font-semibold text-fpl-green bg-fpl-green/10 px-1 rounded">P</span>
                      </Show>
                      <Show when={p.is_set_piece_taker}>
                        <span class="ml-1 text-[11px] font-semibold text-fpl-cyan bg-fpl-cyan/10 px-1 rounded">SP</span>
                      </Show>
                      <Show when={p.news}>
                        <span class="ml-1 text-[11px] text-fpl-pink" title={p.news || ''}>!</span>
                      </Show>
                    </div>
                    <div class="text-xs text-gray-400">
                      {formatCost(p.now_cost)} ·{' '}
                      <span class={`text-xs font-semibold px-1.5 py-0.5 rounded-full ${BADGE_CLASSES[p.position]}`}>
                        {POSITIONS[p.position]}
                      </span>
                    </div>
                  </div>
                  <div class="text-right shrink-0">
                    <div class="text-fpl-green font-bold">{p.form_points ?? '-'}</div>
                    <div class="text-[11px] text-gray-500">form</div>
                  </div>
                </div>
                <div class="grid grid-cols-3 gap-2 ml-12 text-center">
                  <div>
                    <div class="text-[11px] text-gray-500">xGI/90</div>
                    <div class="text-white font-bold text-sm">{p.xgi_per_90 ?? '-'}</div>
                  </div>
                  <div>
                    <div class="text-[11px] text-gray-500">Own%</div>
                    <div class={`font-bold text-sm ${Number(p.selected_by_percent ?? 0) > 30 ? 'text-fpl-green' : Number(p.selected_by_percent ?? 0) < 5 ? 'text-fpl-pink' : 'text-white'}`}>
                      {p.selected_by_percent ?? '-'}%
                    </div>
                  </div>
                  <div>
                    <div class="text-[11px] text-gray-500">Transfers</div>
                    {(() => {
                      const net = (p.transfers_in_event ?? 0) - (p.transfers_out_event ?? 0);
                      return (
                        <div class={`font-bold text-sm ${net > 0 ? 'text-fpl-green' : net < 0 ? 'text-fpl-pink' : 'text-gray-400'}`}>
                          {net > 0 ? '+' : ''}{(net / 1000).toFixed(1)}k
                        </div>
                      );
                    })()}
                  </div>
                </div>
              </a>
            )}
          </For>
        </div>

        {/* Desktop table */}
        <div class="hidden md:block card overflow-hidden" data-testid="players-desktop">
          <div class="overflow-x-auto max-h-[70vh] overflow-y-auto">
            <table class="w-full text-sm">
              <thead class="sticky top-0 bg-fpl-card z-10">
                <tr class="text-left text-gray-400 border-b border-gray-700">
                  <th class="py-3 px-4 font-medium">Player</th>
                  <th class="py-3 px-3 font-medium">Team</th>
                  <th class="py-3 px-3 font-medium">Pos</th>
                  <th class="py-3 px-3 text-right font-medium">Price</th>
                  <th class="py-3 px-3 text-right font-medium">Form</th>
                  <th class="py-3 px-3 text-right font-medium">Pts/G</th>
                  <th class="py-3 px-3 text-right font-medium">xGI/90</th>
                  <th class="py-3 px-3 text-right font-medium">Own%</th>
                  <th class="py-3 px-3 text-right font-medium">Transfers</th>
                </tr>
              </thead>
              <tbody>
                <For each={players()}>
                  {(p) => (
                    <tr class="border-b border-gray-800/40 hover:bg-white/3 transition-colors cursor-pointer" onClick={() => window.location.href = `/players/${slugify(p.id, p.first_name, p.second_name)}`}>
                      <td class="py-2.5 px-4">
                        <div class="flex items-center gap-2.5">
                          <img
                            src={p.shirt_url || ''}
                            alt=""
                            class="w-9 h-9 shrink-0"
                            loading="lazy"
                          />
                          <a href={`/players/${slugify(p.id, p.first_name, p.second_name)}`} class="text-fpl-cyan hover:underline decoration-fpl-cyan/40 underline-offset-2 font-medium" onClick={(e) => e.stopPropagation()}>
                            {p.web_name}
                          </a>
                        </div>
                        <Show when={p.is_penalty_taker}>
                          <span class="ml-1.5 text-[11px] font-semibold text-fpl-green bg-fpl-green/10 px-1 rounded">P</span>
                        </Show>
                        <Show when={p.is_set_piece_taker}>
                          <span class="ml-1 text-[11px] font-semibold text-fpl-cyan bg-fpl-cyan/10 px-1 rounded">SP</span>
                        </Show>
                        <Show when={p.news}>
                          <span class="ml-1.5 text-[11px] text-fpl-pink" title={p.news || ''}>!</span>
                        </Show>
                      </td>
                      <td class="py-2.5 px-3 text-gray-400">{p.team_short_name}</td>
                      <td class="py-2.5 px-3">
                        <span class={`text-xs font-semibold px-2 py-0.5 rounded-full ${BADGE_CLASSES[p.position]}`}>
                          {POSITIONS[p.position]}
                        </span>
                      </td>
                      <td class="py-2.5 px-3 text-right tabular-nums">{formatCost(p.now_cost)}</td>
                      <td class="py-2.5 px-3 text-right font-semibold text-fpl-green tabular-nums">{p.form_points ?? '-'}</td>
                      <td class="py-2.5 px-3 text-right tabular-nums">{p.pts_per_game ?? '-'}</td>
                      <td class="py-2.5 px-3 text-right tabular-nums">{p.xgi_per_90 ?? '-'}</td>
                      <td class="py-2.5 px-3 text-right tabular-nums">
                        <span class={Number(p.selected_by_percent ?? 0) > 30 ? 'text-fpl-green' : Number(p.selected_by_percent ?? 0) < 5 ? 'text-fpl-pink' : ''}>
                          {p.selected_by_percent ?? '-'}%
                        </span>
                      </td>
                      <td class="py-2.5 px-3 text-right tabular-nums">
                        {(() => {
                          const net = (p.transfers_in_event ?? 0) - (p.transfers_out_event ?? 0);
                          return (
                            <span class={net > 0 ? 'text-fpl-green' : net < 0 ? 'text-fpl-pink' : 'text-gray-400'}>
                              {net > 0 ? '+' : ''}{(net / 1000).toFixed(1)}k
                            </span>
                          );
                        })()}
                      </td>
                    </tr>
                  )}
                </For>
              </tbody>
            </table>
          </div>
        </div>
      </Show>
    </div>
  );
}
