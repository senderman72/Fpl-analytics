import { SolidApexCharts } from 'solid-apexcharts';
import { createMemo } from 'solid-js';
import { baseChartOptions, FPL_COLORS } from '../lib/chartTheme';
import type { ApexOptions } from 'apexcharts';

interface GW {
  gameweek_id: number;
  value: number;
}

export default function PriceChart(props: { history: string }) {
  const data = createMemo<GW[]>(() => {
    try { return JSON.parse(props.history); }
    catch { return []; }
  });

  const prices = createMemo(() => data().map(h => h.value / 10));
  const minPrice = createMemo(() => prices().length ? Math.min(...prices()) - 0.2 : 0);
  const maxPrice = createMemo(() => prices().length ? Math.max(...prices()) + 0.2 : 10);

  const options = createMemo<ApexOptions>(() => ({
    ...baseChartOptions,
    chart: { ...baseChartOptions.chart, type: 'line', height: 100, sparkline: { enabled: true } },
    colors: [FPL_COLORS.cyan],
    stroke: { curve: 'smooth', width: 2 },
    tooltip: {
      fixed: { enabled: false },
      x: { show: true, formatter: ((_val, opts) => `GW${data()[(opts as { dataPointIndex: number })?.dataPointIndex ?? 0]?.gameweek_id ?? ''}`) as (val: string | number, opts?: unknown) => string },
      y: { formatter: (val: number) => `£${val.toFixed(1)}m` },
      theme: 'dark',
    },
    yaxis: { min: minPrice(), max: maxPrice(), show: false },
  }));

  const series = createMemo(() => [
    { name: 'Price', data: prices() },
  ]);

  return <SolidApexCharts type="line" options={options()} series={series()} height={100} />;
}
