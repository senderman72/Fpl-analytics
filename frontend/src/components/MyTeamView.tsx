import { createSignal, createResource, For, Show } from 'solid-js';
import type { MyTeamResponse, MyTeamPick } from '../lib/types';
import { getMyTeam } from '../api/my-team';
import { fdrColor, formatCost } from '../lib/types';

function PlayerCard(props: { pick: MyTeamPick; compact?: boolean }) {
  const p = props.pick;
  return (
    <a href={`/players/${p.player_id}`} class="flex flex-col items-center group">
      <div class="relative">
        <img src={p.shirt_url ?? ''} alt="" class="w-8 h-8 sm:w-10 sm:h-10 md:w-14 md:h-14 object-contain" width="110" height="140" />
        {p.is_captain && (
          <span class="absolute -top-1 -right-1 w-4 h-4 sm:w-5 sm:h-5 rounded-full bg-fpl-gold text-fpl-dark text-[9px] sm:text-[11px] font-extrabold flex items-center justify-center">C</span>
        )}
        {p.is_vice_captain && (
          <span class="absolute -top-1 -right-1 w-4 h-4 sm:w-5 sm:h-5 rounded-full bg-gray-400 text-fpl-dark text-[9px] sm:text-[11px] font-extrabold flex items-center justify-center">V</span>
        )}
      </div>
      <div class="bg-fpl-card/90 backdrop-blur-sm rounded px-1 sm:px-1.5 py-0.5 mt-0.5 sm:mt-1 text-center min-w-[44px] sm:min-w-[56px] md:min-w-[70px]">
        <div class="text-white text-[10px] sm:text-xs font-bold truncate max-w-[52px] sm:max-w-[80px] group-hover:text-fpl-cyan transition-colors">{p.web_name}</div>
        {p.predicted_points && (
          <div class="text-fpl-green text-[9px] sm:text-[11px] font-bold">{p.predicted_points} pts</div>
        )}
      </div>
      {!props.compact && p.fixtures.length > 0 && (
        <div class="hidden sm:flex gap-0.5 mt-1">
          <For each={p.fixtures.slice(0, 3)}>
            {(f) => {
              const color = fdrColor(f.difficulty);
              return (
                <span
                  class="text-[8px] font-bold px-1 py-0.5 rounded"
                  style={`background: ${color}18; color: ${color}; border: 1px solid ${color}30`}
                >
                  {f.opponent}{f.is_home ? 'H' : 'A'}
                </span>
              );
            }}
          </For>
        </div>
      )}
    </a>
  );
}

function PitchRow(props: { picks: MyTeamPick[] }) {
  return (
    <div class="flex justify-center gap-0.5 sm:gap-1.5 md:gap-6">
      <For each={props.picks}>
        {(p) => <PlayerCard pick={p} />}
      </For>
    </div>
  );
}

export default function MyTeamView(props: { initialId?: number }) {
  const stored = typeof localStorage !== 'undefined' ? localStorage.getItem('fpl_manager_id') : null;
  const [managerId, setManagerId] = createSignal(props.initialId ?? (stored ? Number(stored) : 0));
  const [inputVal, setInputVal] = createSignal(String(managerId() || ''));
  const [submitted, setSubmitted] = createSignal(!!managerId());

  const [data, { refetch }] = createResource(
    () => submitted() ? managerId() : null,
    (id) => id ? getMyTeam(id) : Promise.resolve(null as unknown as MyTeamResponse),
  );

  function handleSubmit(e: Event) {
    e.preventDefault();
    const id = parseInt(inputVal(), 10);
    if (!id || isNaN(id)) return;
    setManagerId(id);
    setSubmitted(true);
    if (typeof localStorage !== 'undefined') {
      localStorage.setItem('fpl_manager_id', String(id));
    }
    refetch();
  }

  // Group starting XI by position for pitch layout
  const rows = () => {
    const d = data();
    if (!d) return [];
    const gk = d.starting.filter((p: MyTeamPick) => p.position === 1);
    const def_ = d.starting.filter((p: MyTeamPick) => p.position === 2);
    const mid = d.starting.filter((p: MyTeamPick) => p.position === 3);
    const fwd = d.starting.filter((p: MyTeamPick) => p.position === 4);
    return [gk, def_, mid, fwd];
  };

  return (
    <div>
      {/* ID Input form */}
      <form onSubmit={handleSubmit} class="card p-5 mb-6">
        <div class="flex flex-col sm:flex-row gap-3 items-start sm:items-end">
          <div class="flex-1">
            <label class="text-sm text-gray-300 font-medium block mb-1.5">FPL Manager ID</label>
            <input
              type="text"
              inputMode="numeric"
              value={inputVal()}
              onInput={(e) => setInputVal(e.currentTarget.value)}
              placeholder="e.g. 2667202"
              class="w-full bg-fpl-dark border border-gray-700 rounded-lg px-3 py-2 text-white text-sm focus:border-fpl-green focus:outline-none transition-colors"
            />
          </div>
          <button
            type="submit"
            class="px-5 py-3 bg-fpl-green text-fpl-dark font-bold text-sm rounded-lg hover:bg-fpl-green/90 transition-colors shrink-0"
          >
            Load Team
          </button>
        </div>
        <details class="mt-3">
          <summary class="text-xs text-gray-400 cursor-pointer hover:text-gray-300 transition-colors">
            How do I find my FPL ID?
          </summary>
          <div class="mt-2 text-xs text-gray-400 space-y-1 pl-3 border-l-2 border-gray-700">
            <p>1. Log in to <strong class="text-gray-300">fantasy.premierleague.com</strong></p>
            <p>2. Go to the <strong class="text-gray-300">Points</strong> or <strong class="text-gray-300">Transfers</strong> tab</p>
            <p>3. Your ID is the number in the URL:</p>
            <p class="font-mono text-gray-300">fantasy.premierleague.com/entry/<strong class="text-fpl-green">2667202</strong>/event/31</p>
          </div>
        </details>
      </form>

      {/* Loading state */}
      <Show when={data.loading}>
        <div class="card p-8 text-center text-gray-400">Loading your team...</div>
      </Show>

      {/* Error state */}
      <Show when={data.error}>
        <div class="card p-6 text-center text-fpl-pink">{String(data.error)}</div>
      </Show>

      {/* Team data */}
      <Show when={!data.loading && !data.error && data()}>
        {(d) => {
          const t = d();
          return (
            <div>
              {/* Manager info bar */}
              <div class="card p-4 mb-4">
                <div class="flex flex-wrap items-center justify-between gap-3 mb-3 sm:mb-0">
                  <div>
                    <div class="text-white font-bold text-base sm:text-lg">{t.team_name}</div>
                    <div class="text-gray-400 text-sm">{t.manager_name}</div>
                  </div>
                </div>
                <div class="grid grid-cols-4 gap-2 text-center">
                  <div>
                    <div class="text-fpl-green font-extrabold text-base sm:text-lg">{t.overall_points}</div>
                    <div class="text-[10px] sm:text-[11px] text-gray-400 uppercase">Total Pts</div>
                  </div>
                  <div>
                    <div class="text-white font-extrabold text-base sm:text-lg">{(t.overall_rank ?? 0).toLocaleString()}</div>
                    <div class="text-[10px] sm:text-[11px] text-gray-400 uppercase">Rank</div>
                  </div>
                  <div>
                    <div class="text-white font-bold text-base sm:text-lg">{t.gameweek_points}</div>
                    <div class="text-[10px] sm:text-[11px] text-gray-400 uppercase">GW Pts</div>
                  </div>
                  <div>
                    <div class="text-gray-300 font-bold text-base sm:text-lg">{formatCost(t.bank)}</div>
                    <div class="text-[10px] sm:text-[11px] text-gray-400 uppercase">Bank</div>
                  </div>
                </div>
              </div>

              {/* Predicted points banner */}
              <div class="card p-3 mb-4 text-center border-l-3 border-fpl-green">
                <span class="text-gray-400 text-sm">Predicted points (next GW): </span>
                <span class="text-fpl-green font-extrabold text-xl ml-1">{t.total_predicted}</span>
              </div>

              {/* Pitch */}
              <div class="card p-3 sm:p-5 mb-4"
                style="background: linear-gradient(180deg, #1a472a 0%, #2d6a3f 30%, #2d6a3f 70%, #1a472a 100%); border: 2px solid #ffffff10;">
                {/* Field markings */}
                <div class="relative py-2 sm:py-4">
                  {/* Center circle - decorative */}
                  <div class="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-16 sm:w-24 h-16 sm:h-24 rounded-full border border-white/10"></div>
                  <div class="absolute top-1/2 left-0 right-0 border-t border-white/10"></div>

                  <div class="relative z-10 space-y-3 sm:space-y-6 md:space-y-8">
                    <For each={rows()}>
                      {(rowPicks) => <PitchRow picks={rowPicks} />}
                    </For>
                  </div>
                </div>
              </div>

              {/* Bench */}
              <div class="card p-3 sm:p-4">
                <div class="text-xs text-gray-400 uppercase tracking-wider mb-2 sm:mb-3">Bench</div>
                <div class="flex justify-center gap-2 sm:gap-4 md:gap-6">
                  <For each={t.bench}>
                    {(p) => <PlayerCard pick={p} compact />}
                  </For>
                </div>
              </div>
            </div>
          );
        }}
      </Show>
    </div>
  );
}
