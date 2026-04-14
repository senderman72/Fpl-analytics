import { lazy, Suspense } from 'solid-js';
import type { ApexOptions } from 'apexcharts';

const SolidApexCharts = lazy(() =>
  import('solid-apexcharts').then((m) => ({ default: m.SolidApexCharts }))
);

interface Props {
  type: string;
  options: ApexOptions;
  series: ApexOptions['series'];
  height: number;
}

export default function LazyChart(props: Props) {
  return (
    <Suspense
      fallback={
        <div
          style={{
            height: `${props.height}px`,
            display: 'flex',
            'align-items': 'center',
            'justify-content': 'center',
            color: '#6b7280',
          }}
        >
          Loading chart...
        </div>
      }
    >
      <SolidApexCharts
        type={props.type as 'line' | 'bar' | 'radar' | 'area'}
        options={props.options}
        series={props.series}
        height={props.height}
      />
    </Suspense>
  );
}
