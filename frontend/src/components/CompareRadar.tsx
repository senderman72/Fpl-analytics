import { createMemo } from 'solid-js';
import LazyChart from './LazyChart';
import { baseChartOptions, FPL_COLORS } from '../lib/chartTheme';
import type { ApexOptions } from 'apexcharts';
import type { PlayerComparison } from '../lib/types';

const RADAR_COLORS = [FPL_COLORS.green, FPL_COLORS.cyan, FPL_COLORS.pink, FPL_COLORS.gold, '#a78bfa'];

interface Props {
  players: PlayerComparison[];
}

/** Normalize a value to 0-100 scale given min/max thresholds. */
function norm(val: number | null, min: number, max: number): number {
  if (val === null || isNaN(val)) return 0;
  const clamped = Math.max(min, Math.min(max, val));
  return Math.round(((clamped - min) / (max - min)) * 100);
}

/** FDR is inverted: lower difficulty = better = higher score. Null = no fixtures = 0. */
function normFdr(val: number | null): number {
  if (val === null || isNaN(val)) return 0;
  const clamped = Math.max(1, Math.min(5, val));
  return Math.round(((5 - clamped) / 4) * 100);
}

export default function CompareRadar(props: Props) {
  const series = createMemo(() =>
    props.players.map((p, i) => ({
      name: p.web_name,
      data: [
        norm(p.form_points, 0, 50),
        norm(parseFloat(p.xgi_per_90 || '0'), 0, 1.2),
        norm(parseFloat(p.minutes_pct || '0'), 0, 100),
        norm(parseFloat(p.bps_avg || '0'), 0, 40),
        normFdr(parseFloat(p.fdr_next_5 || '3')),
        norm(parseFloat(p.pts_per_game || '0'), 0, 10),
      ],
    }))
  );

  const options = createMemo<ApexOptions>(() => ({
    ...baseChartOptions,
    chart: { ...baseChartOptions.chart, type: 'radar', height: 340 },
    colors: RADAR_COLORS.slice(0, props.players.length),
    xaxis: {
      categories: ['Form', 'xGI/90', 'Minutes%', 'BPS', 'Fixtures', 'Pts/Game'],
      labels: { style: { colors: '#9ca3af', fontSize: '11px' } },
    },
    yaxis: { show: false, min: 0, max: 100 },
    stroke: { width: 2 },
    fill: { opacity: 0.15 },
    markers: { size: 3 },
    legend: {
      ...baseChartOptions.legend,
      position: 'bottom',
    },
    tooltip: {
      ...baseChartOptions.tooltip,
      y: { formatter: (val: number) => `${val}` },
    },
  }));

  return <LazyChart type="radar" options={options()} series={series()} height={340} />;
}
