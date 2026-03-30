import { SolidApexCharts } from 'solid-apexcharts';
import { createMemo } from 'solid-js';
import { baseChartOptions, FPL_COLORS } from '../lib/chartTheme';
import type { ApexOptions } from 'apexcharts';

interface GW {
  gameweek_id: number;
  total_points: number;
}

export default function PointsChart(props: { history: string }) {
  const data = createMemo<GW[]>(() => {
    try { return JSON.parse(props.history); }
    catch { return []; }
  });

  const options = createMemo<ApexOptions>(() => ({
    ...baseChartOptions,
    chart: { ...baseChartOptions.chart, type: 'area', height: 220 },
    colors: [FPL_COLORS.green],
    fill: {
      type: 'gradient',
      gradient: { shadeIntensity: 1, opacityFrom: 0.4, opacityTo: 0.05, stops: [0, 100] },
    },
    xaxis: {
      ...baseChartOptions.xaxis,
      categories: data().map(h => `GW${h.gameweek_id}`),
      tickAmount: Math.min(data().length, 10),
    },
    yaxis: {
      ...baseChartOptions.yaxis,
      min: 0,
    },
    markers: {
      size: data().map(h => h.total_points >= 10 ? 5 : 0),
      colors: [FPL_COLORS.green],
      strokeColors: FPL_COLORS.dark,
      strokeWidth: 2,
    },
    tooltip: {
      ...baseChartOptions.tooltip,
      y: { formatter: (val: number) => `${val} pts` },
    },
  }));

  const series = createMemo(() => [
    { name: 'Points', data: data().map(h => h.total_points) },
  ]);

  return <SolidApexCharts type="area" options={options()} series={series()} height={220} />;
}
