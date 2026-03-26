/** Shared TypeScript types matching backend Pydantic schemas. */

export interface PlayerSummary {
  id: number;
  web_name: string;
  first_name: string;
  second_name: string;
  team_id: number;
  team_short_name: string | null;
  position: number;
  now_cost: number;
  status: string;
  chance_of_playing_next_round: number | null;
  news: string | null;
  is_penalty_taker: boolean;
  is_set_piece_taker: boolean;
  form_points: number | null;
  pts_per_game: string | null;
  xgi_per_90: string | null;
  minutes_pct: string | null;
  bps_avg: string | null;
}

export interface PlayerDetail extends PlayerSummary {
  understat_id: number | null;
  season_xg: string | null;
  season_xa: string | null;
  season_xgi: string | null;
  season_npxg: string | null;
  season_games: number | null;
  season_minutes: number | null;
}

export interface PlayerGWHistory {
  gameweek_id: number;
  fixture_id: number | null;
  minutes: number;
  goals_scored: number;
  assists: number;
  clean_sheets: number;
  goals_conceded: number;
  bonus: number;
  bps: number;
  influence: string;
  creativity: string;
  threat: string;
  ict_index: string;
  total_points: number;
  transfers_in: number;
  transfers_out: number;
  value: number;
}

export interface PlayerFixture {
  fixture_id: number;
  gameweek_id: number | null;
  opponent_team_id: number;
  opponent_short_name: string;
  is_home: boolean;
  difficulty: number | null;
  kickoff_time: string | null;
  is_double_gw: boolean;
}

export interface GameweekOut {
  id: number;
  name: string;
  deadline_time: string;
  is_current: boolean;
  is_next: boolean;
  is_finished: boolean;
  is_double: boolean;
  is_blank: boolean;
  average_entry_score: number | null;
  highest_score: number | null;
}

export interface BuyCandidate {
  player_id: number;
  web_name: string;
  team_short_name: string;
  position: number;
  now_cost: number;
  form_points: number;
  pts_per_game: string;
  xgi_per_90: string;
  minutes_pct: string;
  ppm: string;
  fdr_next_5: string | null;
}

export interface CaptainPick {
  player_id: number;
  web_name: string;
  team_short_name: string;
  position: number;
  now_cost: number;
  ceiling_score: number;
  bps_avg: string;
  form_points: number;
  is_home: boolean | null;
  is_double_gw: boolean;
  is_penalty_taker: boolean;
  is_set_piece_taker: boolean;
  predicted_points: string | null;
}

export interface ChipAdvice {
  gameweek_id: number;
  name: string;
  is_double: boolean;
  is_blank: boolean;
  recommendation: string | null;
}

export interface PredictionOut {
  player_id: number;
  web_name: string;
  team_short_name: string;
  position: number;
  predicted_points: string;
  now_cost: number;
}

export const POSITIONS: Record<number, string> = {
  1: 'GK', 2: 'DEF', 3: 'MID', 4: 'FWD',
};

export const POSITION_COLORS: Record<number, string> = {
  1: '#f59e0b', 2: '#3b82f6', 3: '#10b981', 4: '#ef4444',
};

export function formatCost(tenths: number): string {
  return `£${(tenths / 10).toFixed(1)}m`;
}

export function fdrColor(fdr: number | null): string {
  if (fdr === null) return '#6b7280';
  if (fdr <= 2) return '#10b981';
  if (fdr === 3) return '#6b7280';
  if (fdr === 4) return '#f59e0b';
  return '#ef4444';
}
