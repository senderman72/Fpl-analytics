import { get } from './client';
import type { PlayerComparison } from '../lib/types';

export function comparePlayers(ids: number[]) {
  return get<PlayerComparison[]>('/players/compare', { ids: ids.join(',') });
}
