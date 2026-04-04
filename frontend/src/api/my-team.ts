import { get } from './client';
import type { MyTeamResponse, TransferPlan } from '../lib/types';

export function getMyTeam(managerId: number) {
  return get<MyTeamResponse>(`/my-team/${managerId}`);
}

export function getTransferSuggestions(managerId: number) {
  return get<TransferPlan>(`/my-team/${managerId}/transfers`);
}
