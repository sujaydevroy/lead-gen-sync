'use client';

import { useEffect, useRef } from 'react';
import * as echarts from 'echarts/core';
import { BarChart, LineChart } from 'echarts/charts';
import { GridComponent, TooltipComponent, MarkLineComponent } from 'echarts/components';
import { SVGRenderer } from 'echarts/renderers';

// Tree-shaken ECharts: only the chart types / components the portal uses are bundled.
echarts.use([BarChart, LineChart, GridComponent, TooltipComponent, MarkLineComponent, SVGRenderer]);

/**
 * Minimal React wrapper around an ECharts instance: creates it on mount, replaces the option when it
 * changes, follows the container's width and disposes on unmount.
 * @param {{ option: object, height: number, ariaLabel?: string }} props
 */
export default function EChart({ option, height, ariaLabel }) {
  const containerRef = useRef(null);
  const chartRef = useRef(null);

  useEffect(() => {
    const chart = echarts.init(containerRef.current, null, { renderer: 'svg' });
    chartRef.current = chart;
    const observer = new ResizeObserver(() => chart.resize());
    observer.observe(containerRef.current);
    return () => {
      observer.disconnect();
      chart.dispose();
      chartRef.current = null;
    };
  }, []);

  useEffect(() => {
    chartRef.current?.setOption(option, { notMerge: true });
  }, [option]);

  useEffect(() => {
    chartRef.current?.resize();
  }, [height]);

  return <div ref={containerRef} role="img" aria-label={ariaLabel} style={{ width: '100%', height }} />;
}
