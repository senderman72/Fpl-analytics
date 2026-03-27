import { get } from './client';
import type { BuyCandidate, CaptainPick, ChipAdvice, DifferentialPick, PriceChangePrediction } from '../lib/types';

export function getBuyCandidates(params?: {
  position?: number;
  max_cost?: number;
  limit?: number;
}) {
  return get<BuyCandidate[]>('/decisions/buys', params);
}

export function getCaptainPicks(limit = 15) {
  return get<CaptainPick[]>('/decisions/captains', { limit });
}

export function getChipAdvice() {
  return get<ChipAdvice[]>('/decisions/chips');
}

export function getDifferentials(params?: {
  max_ownership?: number;
  limit?: number;
}) {
  return get<DifferentialPick[]>('/decisions/differentials', params);
}

export function getPriceChanges() {
  return get<PriceChangePrediction>('/decisions/price-changes');
}
