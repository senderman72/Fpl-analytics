import { get } from './client';
import type { GameweekOut, FixtureOut } from '../lib/types';

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
