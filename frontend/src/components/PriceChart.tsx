import { SolidApexCharts } from 'solid-apexcharts';
import { createMemo } from 'solid-js';
import { baseChartOptions, FPL_COLORS } from '../lib/chartTheme';
import type { ApexOptions } from 'apexcharts';

interface GW {
  gameweek_id: number;
  value: number;
}

export default function PriceChart(props: { history: string }) {
  const data = createMemo<GW[]>(() => JSON.parse(props.history));

  const prices = createMemo(() => data().map(h => h.value / 10));
  const minPrice = createMemo(() => Math.min(...prices()) - 0.2);
  const maxPrice = createMemo(() => Math.max(...prices()) + 0.2);

  const options = createMemo<ApexOptions>(() => ({
    ...baseChartOptions,
    chart: { ...baseChartOptions.chart, type: 'line', height: 100, sparkline: { enabled: true } },
    colors: [FPL_COLORS.cyan],
    stroke: { curve: 'smooth', width: 2 },
    tooltip: {
      fixed: { enabled: false },
      x: { show: true, formatter: (_: number, opts: { dataPointIndex: number }) => `GW${data()[opts.dataPointIndex]?.gameweek_id}` },
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
