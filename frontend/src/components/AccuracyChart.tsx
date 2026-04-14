import { createMemo } from 'solid-js';
import LazyChart from './LazyChart';
import { baseChartOptions, FPL_COLORS } from '../lib/chartTheme';
import { POSITION_COLORS } from '../lib/types';
import type { ApexOptions } from 'apexcharts';
import type { GWAccuracy, PositionAccuracy } from '../lib/types';

interface Props {
  perGameweek: string;
  byPosition: string;
}

export default function AccuracyChart(props: Props) {
  const gwData = createMemo<GWAccuracy[]>(() => {
    try { return JSON.parse(props.perGameweek); }
    catch { return []; }
  });

  const posData = createMemo<PositionAccuracy[]>(() => {
    try { return JSON.parse(props.byPosition); }
    catch { return []; }
  });

  const lineOptions = createMemo<ApexOptions>(() => ({
    ...baseChartOptions,
    chart: { ...baseChartOptions.chart, type: 'line', height: 260 },
    colors: [FPL_COLORS.cyan],
    xaxis: {
      ...baseChartOptions.xaxis,
      categories: gwData().map(g => `GW${g.gameweek_id}`),
      tickAmount: Math.min(gwData().length, 12),
    },
    yaxis: {
      ...baseChartOptions.yaxis,
      min: 0,
      title: { text: 'MAE', style: { color: '#9ca3af', fontSize: '11px' } },
    },
    tooltip: {
      ...baseChartOptions.tooltip,
      y: { formatter: (val: number) => `${val.toFixed(2)} pts` },
    },
    markers: { size: 4, colors: [FPL_COLORS.cyan], strokeColors: FPL_COLORS.dark, strokeWidth: 2 },
  }));

  const lineSeries = createMemo(() => [
    { name: 'MAE', data: gwData().map(g => parseFloat(g.mae)) },
  ]);

  const barOptions = createMemo<ApexOptions>(() => ({
    ...baseChartOptions,
    chart: { ...baseChartOptions.chart, type: 'bar', height: 260 },
    colors: posData().map(p => POSITION_COLORS[p.position] || '#6b7280'),
    plotOptions: {
      bar: { distributed: true, borderRadius: 4, columnWidth: '60%' },
    },
    xaxis: {
      ...baseChartOptions.xaxis,
      categories: posData().map(p => p.position_name),
    },
    yaxis: {
      ...baseChartOptions.yaxis,
      min: 0,
      title: { text: 'MAE', style: { color: '#9ca3af', fontSize: '11px' } },
    },
    tooltip: {
      ...baseChartOptions.tooltip,
      y: { formatter: (val: number) => `${val.toFixed(2)} pts` },
    },
    legend: { show: false },
  }));

  const barSeries = createMemo(() => [
    { name: 'MAE', data: posData().map(p => parseFloat(p.mae)) },
  ]);

  return (
    <div style={{ display: 'grid', 'grid-template-columns': '1fr 1fr', gap: '1.5rem' }}>
      <div>
        <h3 style={{ color: '#9ca3af', 'font-size': '0.75rem', 'margin-bottom': '0.5rem', 'font-weight': '500' }}>MAE Over Time</h3>
        <LazyChart type="line" options={lineOptions()} series={lineSeries()} height={260} />
      </div>
      <div>
        <h3 style={{ color: '#9ca3af', 'font-size': '0.75rem', 'margin-bottom': '0.5rem', 'font-weight': '500' }}>MAE By Position</h3>
        <LazyChart type="bar" options={barOptions()} series={barSeries()} height={260} />
      </div>
    </div>
  );
}
