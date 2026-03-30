import { get } from './client';
import type { MyTeamResponse } from '../lib/types';

export function getMyTeam(managerId: number) {
  return get<MyTeamResponse>(`/my-team/${managerId}`);
}
