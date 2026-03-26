import { get } from './client';
import type { GameweekOut } from '../lib/types';

export function getGameweeks() {
  return get<GameweekOut[]>('/gameweeks');
}
