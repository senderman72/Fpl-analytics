import { createSignal, createResource, For, Show, onCleanup } from 'solid-js';
import type { LiveGWResponse } from '../lib/types';

import { getLiveGW } from '../api/gameweeks';

function hasLiveFixtures(data: LiveGWResponse | undefined): boolean {
  if (!data) return false;
  return data.fixtures.some(f => f.started && !f.finished);
}

function allFixturesFinished(data: LiveGWResponse | undefined): boolean {
  if (!data || data.fixtures.length === 0) return false;
  return data.fixtures.every(f => f.finished);
}

function anyFixtureStarted(data: LiveGWResponse | undefined): boolean {
  if (!data) return false;
  return data.fixtures.some(f => f.started);
}

export default function LiveTracker(props: { currentGwId: number }) {
  const [lastUpdated, setLastUpdated] = createSignal(Date.now());
  const [polling, setPolling] = createSignal(false);

  const [data, { refetch }] = createResource(
    () => props.currentGwId,
    (gwId) => getLiveGW(gwId),
  );

  // Smart polling: only poll when fixtures are in progress
  let pollInterval: ReturnType<typeof setInterval> | null = null;

  function startPolling() {
    if (pollInterval) return;
    setPolling(true);
    pollInterval = setInterval(async () => {
      try {
        await refetch();
        setLastUpdated(Date.now());
        if (allFixturesFinished(data())) {
          stopPolling();
        }
      } catch {
        // Polling failure is non-fatal; will retry next interval
      }
    }, 60_000);
  }

  function stopPolling() {
    if (pollInterval) {
      clearInterval(pollInterval);
      pollInterval = null;
    }
    setPolling(false);
  }

  onCleanup(() => stopPolling());

  // After initial fetch, decide whether to poll
  const checkPolling = () => {
    const d = data();
    if (!d) return;
    if (hasLiveFixtures(d)) {
      startPolling();
    } else {
      stopPolling();
    }
  };

  // Watch for data changes to start/stop polling
  // Using a reactive effect via createResource's resolved state
  const resolvedData = () => {
    const d = data();
    if (d) checkPolling();
    return d;
  };

  const secondsAgo = () => Math.floor((Date.now() - lastUpdated()) / 1000);

  // Tick to update "seconds ago" display
  const [, setTick] = createSignal(0);
  const tickInterval = setInterval(() => setTick(t => t + 1), 10_000);
  onCleanup(() => clearInterval(tickInterval));

  const gwStatus = () => {
    const d = resolvedData();
    if (!d) return 'loading';
    if (hasLiveFixtures(d)) return 'live';
    if (allFixturesFinished(d)) return 'finished';
    if (anyFixtureStarted(d)) return 'partial'; // some finished, none in progress
    return 'upcoming';
  };

  return (
    <div>
      {/* Status bar */}
      <div class="flex items-center justify-between mb-4 text-xs text-gray-400">
        <div class="flex items-center gap-2">
          <span>Gameweek {props.currentGwId}</span>
          {gwStatus() === 'live' && (
            <span class="flex items-center gap-1.5 text-fpl-green font-bold">
              <span class="w-1.5 h-1.5 rounded-full bg-fpl-green animate-pulse"></span>
              LIVE
            </span>
          )}
          {gwStatus() === 'finished' && (
            <span class="text-gray-500">All matches finished</span>
          )}
          {gwStatus() === 'upcoming' && (
            <span class="text-gray-500">Matches not started yet</span>
          )}
        </div>
        <Show when={!data.loading} fallback={<span>Loading...</span>}>
          {polling() ? (
            <span>Updated {secondsAgo()}s ago · auto-refreshing</span>
          ) : (
            <span>Last updated {secondsAgo()}s ago</span>
          )}
        </Show>
      </div>

      <Show when={resolvedData()} fallback={
        <div class="card p-8 text-center text-gray-400">Loading live data...</div>
      }>
        {(liveData) => (
          <>
            {/* Fixture scores */}
            <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 mb-8">
              <For each={liveData().fixtures}>
                {(f) => (
                  <div class="card p-4">
                    <div class="flex items-center justify-between gap-3">
                      <div class="flex items-center gap-2 flex-1 min-w-0">
                        <span class="font-bold text-white truncate">{f.home_team_short}</span>
                      </div>
                      <div class="text-center shrink-0 min-w-[60px]">
                        <Show when={f.started} fallback={
                          <span class="text-gray-500 text-sm">vs</span>
                        }>
                          <span class="text-white font-extrabold text-xl tabular-nums">
                            {f.home_goals} - {f.away_goals}
                          </span>
                        </Show>
                        <div class="text-[11px] mt-0.5">
                          {f.finished
                            ? <span class="text-gray-500">FT</span>
                            : f.started
                              ? <span class="text-fpl-green font-bold">LIVE</span>
                              : <span class="text-gray-600">-</span>
                          }
                        </div>
                      </div>
                      <div class="flex items-center gap-2 flex-1 min-w-0 justify-end">
                        <span class="font-bold text-white truncate text-right">{f.away_team_short}</span>
                      </div>
                    </div>
                  </div>
                )}
              </For>
            </div>

            {/* Top players — Mobile cards */}
            <div class="md:hidden" data-testid="live-scorers-mobile">
              <h3 class="text-sm font-bold text-white mb-3">Top Scorers</h3>
              <div class="space-y-2">
                <For each={liveData().players.slice(0, 30)}>
                  {(p, i) => (
                    <a href={`/players/${p.player_id}`} class="card p-3 block hover:bg-white/3 transition-colors">
                      <div class="flex items-center gap-3">
                        <span class="text-gray-500 text-xs w-5 text-right shrink-0">{i() + 1}</span>
                        <img src={p.shirt_url || ''} alt="" class="w-8 h-8 shrink-0" loading="lazy" />
                        <div class="flex-1 min-w-0">
                          <div class="text-fpl-cyan font-medium truncate">{p.web_name}</div>
                          <div class="flex gap-3 text-xs text-gray-400 mt-0.5">
                            <span>{p.minutes}'</span>
                            {p.goals_scored > 0 && <span class="text-white">{p.goals_scored}G</span>}
                            {p.assists > 0 && <span class="text-white">{p.assists}A</span>}
                            {p.bonus > 0 && <span>{p.bonus} bonus</span>}
                          </div>
                        </div>
                        <div class="text-right shrink-0">
                          <div class="text-fpl-green font-bold text-lg tabular-nums">{p.total_points}</div>
                          <div class="text-[11px] text-gray-500">pts</div>
                        </div>
                      </div>
                    </a>
                  )}
                </For>
              </div>
            </div>

            {/* Top players — Desktop table */}
            <div class="hidden md:block card overflow-hidden" data-testid="live-scorers-desktop">
              <h3 class="px-5 py-3 border-b border-gray-700/60 text-sm font-bold text-white">
                Top Scorers
              </h3>
              <div class="overflow-x-auto">
                <table class="w-full text-sm">
                  <thead class="bg-fpl-card">
                    <tr class="text-left text-gray-400 border-b border-gray-700">
                      <th class="py-2.5 px-3 font-medium">#</th>
                      <th class="py-2.5 px-3 font-medium">Player</th>
                      <th class="py-2.5 px-3 text-right font-medium">Mins</th>
                      <th class="py-2.5 px-3 text-right font-medium">G</th>
                      <th class="py-2.5 px-3 text-right font-medium">A</th>
                      <th class="py-2.5 px-3 text-right font-medium">Bonus</th>
                      <th class="py-2.5 px-3 text-right font-medium">Pts</th>
                    </tr>
                  </thead>
                  <tbody>
                    <For each={liveData().players.slice(0, 30)}>
                      {(p, i) => (
                        <tr class="border-b border-gray-800/40 hover:bg-white/3 transition-colors">
                          <td class="py-2 px-3 text-gray-500">{i() + 1}</td>
                          <td class="py-2 px-3">
                            <a href={`/players/${p.player_id}`} class="flex items-center gap-2">
                              <img src={p.shirt_url || ''} alt="" class="w-7 h-7 shrink-0" loading="lazy" />
                              <span class="text-fpl-cyan font-medium hover:underline">{p.web_name}</span>
                            </a>
                          </td>
                          <td class="py-2 px-3 text-right tabular-nums">{p.minutes}'</td>
                          <td class="py-2 px-3 text-right tabular-nums">{p.goals_scored || '-'}</td>
                          <td class="py-2 px-3 text-right tabular-nums">{p.assists || '-'}</td>
                          <td class="py-2 px-3 text-right tabular-nums">{p.bonus || '-'}</td>
                          <td class="py-2 px-3 text-right">
                            <span class="text-lg font-bold text-fpl-green tabular-nums">{p.total_points}</span>
                          </td>
                        </tr>
                      )}
                    </For>
                  </tbody>
                </table>
              </div>
            </div>
          </>
        )}
      </Show>

      <Show when={data.error}>
        <div class="card p-8 text-center text-fpl-pink">
          Failed to load live data.{polling() ? ' Will retry in 60s.' : ''}
        </div>
      </Show>
    </div>
  );
}
