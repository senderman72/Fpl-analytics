import { get } from './client';
import type { GameweekOut, FixtureOut, LiveGWResponse } from '../lib/types';

export function getGameweeks() {
  return get<GameweekOut[]>('/gameweeks');
}

export function getFixtures(params?: {
  gameweek_id?: number;
  team_id?: number;
  finished?: boolean;
}) {
  return get<FixtureOut[]>('/fixtures', params);
}

export function getLiveGW(gwId: number) {
  return get<LiveGWResponse>(`/live/${gwId}`);
}
