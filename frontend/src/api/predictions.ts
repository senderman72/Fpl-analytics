import { get } from './client';
import type { PredictionOut } from '../lib/types';

export function getPredictions(gwId: number, params?: {
  position?: number;
  limit?: number;
}) {
  return get<PredictionOut[]>(`/predictions/gw/${gwId}`, params);
}
