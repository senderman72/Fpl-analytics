import { get } from './client';
import type { PredictedLineup } from '../lib/types';

export function getLineups(teamId?: number) {
  return get<PredictedLineup[]>(
    '/lineups/predicted',
    teamId ? { team_id: teamId } : undefined,
  );
}
