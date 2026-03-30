/** Shared ApexCharts theme for the FPL dark UI. */

import type { ApexOptions } from 'apexcharts';

export const FPL_COLORS = {
  green: '#00ff87',
  cyan: '#04f5ff',
  pink: '#e90052',
  gold: '#ffd700',
  purple: '#37003c',
  dark: '#1a1a2e',
  card: '#16213e',
} as const;

export const baseChartOptions: ApexOptions = {
  chart: {
    background: 'transparent',
    toolbar: { show: false },
    zoom: { enabled: false },
    fontFamily: 'inherit',
  },
  theme: { mode: 'dark' },
  grid: {
    borderColor: 'rgba(107,114,128,0.15)',
    strokeDashArray: 3,
  },
  xaxis: {
    labels: { style: { colors: '#9ca3af', fontSize: '11px' } },
    axisBorder: { show: false },
    axisTicks: { show: false },
  },
  yaxis: {
    labels: { style: { colors: '#9ca3af', fontSize: '11px' } },
  },
  tooltip: {
    theme: 'dark',
    style: { fontSize: '12px' },
  },
  dataLabels: { enabled: false },
  stroke: { curve: 'smooth', width: 2 },
  legend: {
    labels: { colors: '#9ca3af' },
    fontSize: '12px',
  },
};
