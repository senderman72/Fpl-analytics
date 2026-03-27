import { SolidApexCharts } from 'solid-apexcharts';
import { createMemo } from 'solid-js';
import { baseChartOptions, FPL_COLORS } from '../lib/chartTheme';
import type { ApexOptions } from 'apexcharts';

interface Props {
  goals: number;
  xg: number;
  assists: number;
  xa: number;
}

export default function XGIChart(props: Props) {
  const options = createMemo<ApexOptions>(() => ({
    ...baseChartOptions,
    chart: { ...baseChartOptions.chart, type: 'bar', height: 180 },
    colors: [FPL_COLORS.green, FPL_COLORS.cyan],
    plotOptions: {
      bar: { horizontal: false, columnWidth: '55%', borderRadius: 4 },
    },
    xaxis: {
      ...baseChartOptions.xaxis,
      categories: ['Goals', 'Assists'],
    },
    yaxis: {
      ...baseChartOptions.yaxis,
      min: 0,
    },
    tooltip: {
      ...baseChartOptions.tooltip,
      y: { formatter: (val: number) => val.toFixed(1) },
    },
    legend: {
      ...baseChartOptions.legend,
      position: 'top',
    },
  }));

  const series = createMemo(() => [
    { name: 'Actual', data: [props.goals, props.assists] },
    { name: 'Expected', data: [Number(props.xg), Number(props.xa)] },
  ]);

  return <SolidApexCharts type="bar" options={options()} series={series()} height={180} />;
}
