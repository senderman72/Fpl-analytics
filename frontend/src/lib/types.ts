/** Shared TypeScript types matching backend Pydantic schemas. */

export interface PlayerSummary {
  id: number;
  web_name: string;
  first_name: string;
  second_name: string;
  team_id: number;
  team_short_name: string | null;
  position: number;
  shirt_url: string | null;
  team_badge_url: string | null;
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
  selected_by_percent: string | null;
  transfers_in_event: number | null;
  transfers_out_event: number | null;
  cost_change_event: number | null;
}

export interface PlayerDetail extends PlayerSummary {
  understat_id: number | null;
  season_xg: string | null;
  season_xa: string | null;
  season_xgi: string | null;
  season_npxg: string | null;
  season_games: number | null;
  season_minutes: number | null;
  season_goals: number | null;
  season_assists: number | null;
  season_points: number | null;
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

export interface PlayerIdName {
  id: number;
  first_name: string;
  second_name: string;
}

export interface BuyCandidate {
  player_id: number;
  web_name: string;
  first_name: string;
  second_name: string;
  shirt_url: string | null;
  team_short_name: string;
  position: number;
  now_cost: number;
  form_points: number;
  pts_per_game: string;
  xgi_per_90: string;
  minutes_pct: string;
  ppm: string;
  fdr_next_5: string | null;
  predicted_points: string | null;
  selected_by_percent: string | null;
  transfers_in_event: number | null;
  recommendation: string;
}

export interface CaptainPick {
  player_id: number;
  web_name: string;
  first_name: string;
  second_name: string;
  shirt_url: string | null;
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
  recommendation: string;
}

export interface ChipAdvice {
  gameweek_id: number;
  name: string;
  is_double: boolean;
  is_blank: boolean;
  recommendation: string | null;
}

export interface DifferentialPick {
  player_id: number;
  web_name: string;
  first_name: string;
  second_name: string;
  shirt_url: string | null;
  team_short_name: string;
  position: number;
  now_cost: number;
  selected_by_percent: string;
  form_points: number;
  xgi_per_90: string;
}

export interface GWPrediction {
  gw_id: number;
  predicted_points: string;
}

export interface PredictionOut {
  player_id: number;
  web_name: string;
  shirt_url: string | null;
  team_short_name: string;
  position: number;
  predicted_points: string;
  predicted_per_gw: GWPrediction[];
  horizon: number;
  now_cost: number;
}

export interface FixtureOut {
  id: number;
  gameweek_id: number | null;
  home_team_id: number;
  away_team_id: number;
  home_short_name: string | null;
  away_short_name: string | null;
  home_badge_url: string | null;
  away_badge_url: string | null;
  kickoff_time: string | null;
  started: boolean;
  finished: boolean;
  home_goals: number | null;
  away_goals: number | null;
  home_difficulty: number | null;
  away_difficulty: number | null;
}

export interface PriceChangeCandidate {
  player_id: number;
  web_name: string;
  shirt_url: string | null;
  team_short_name: string;
  position: number;
  now_cost: number;
  selected_by_percent: string | null;
  transfers_in_event: number;
  transfers_out_event: number;
  net_transfers: number;
  cost_change_event: number;
  likelihood: string;
}

export interface PriceChangePrediction {
  risers: PriceChangeCandidate[];
  fallers: PriceChangeCandidate[];
}

export interface MyTeamPick {
  player_id: number;
  web_name: string;
  shirt_url: string | null;
  team_short_name: string;
  position: number;
  slot: number;
  is_captain: boolean;
  is_vice_captain: boolean;
  multiplier: number;
  now_cost: number;
  form_points: number | null;
  predicted_points: string | null;
  fixtures: { opponent: string; difficulty: number; is_home: boolean }[];
}

export interface MyTeamResponse {
  manager_name: string;
  team_name: string;
  overall_rank: number;
  overall_points: number;
  gameweek_points: number;
  bank: number;
  team_value: number;
  starting: MyTeamPick[];
  bench: MyTeamPick[];
  total_predicted: string;
}

export interface LivePlayerScore {
  player_id: number;
  web_name: string;
  shirt_url: string;
  minutes: number;
  goals_scored: number;
  assists: number;
  bonus: number;
  bps: number;
  total_points: number;
}

export interface LiveFixture {
  fixture_id: number;
  home_team_short: string;
  away_team_short: string;
  home_badge_url: string | null;
  away_badge_url: string | null;
  home_goals: number;
  away_goals: number;
  started: boolean;
  finished: boolean;
  minutes: number;
}

export interface LiveGWResponse {
  gameweek_id: number;
  fixtures: LiveFixture[];
  players: LivePlayerScore[];
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
