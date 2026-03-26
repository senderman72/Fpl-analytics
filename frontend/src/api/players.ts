import { get } from './client';
import type { PlayerSummary, PlayerDetail, PlayerGWHistory, PlayerFixture } from '../lib/types';

export function getPlayers(params?: {
  position?: number;
  team_id?: number;
  search?: string;
  sort_by?: string;
  limit?: number;
  offset?: number;
}) {
  return get<PlayerSummary[]>('/players', params);
}

export function getPlayer(id: number) {
  return get<PlayerDetail>(`/players/${id}`);
}

export function getPlayerHistory(id: number) {
  return get<PlayerGWHistory[]>(`/players/${id}/history`);
}

export function getPlayerFixtures(id: number, limit = 8) {
  return get<PlayerFixture[]>(`/players/${id}/fixtures`, { limit });
}
