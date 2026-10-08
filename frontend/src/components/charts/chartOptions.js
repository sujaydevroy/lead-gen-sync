import { chartColors } from '@/lib/theme';
import { formatNumber } from '@/lib/format';

const FONT_FAMILY = '"Inter", "Segoe UI", system-ui, -apple-system, Roboto, "Helvetica Neue", Arial, sans-serif';

const escapeHtml = (value) =>
  String(value).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);

/**
 * Tooltip card markup shared by all charts (ECharts tooltips are HTML strings, so every value is escaped).
 * `rows` = [{ label, value, color?, dashed? }]
 */
export function tooltipHtml(title, rows) {
  const items = rows
    .map(({ label, value, color, dashed }) => {
      const swatch = color
        ? `<span aria-hidden style="display:inline-block;width:12px;border-top:2px ${dashed ? 'dashed' : 'solid'} ${color}"></span>`
        : '';
      return (
        `<div style="display:flex;justify-content:space-between;align-items:center;gap:16px">` +
        `<span style="display:flex;align-items:center;gap:6px;color:#52607a">${swatch}${escapeHtml(label)}</span>` +
        `<span style="font-weight:600;color:${chartColors.text};font-variant-numeric:tabular-nums">${escapeHtml(value)}</span>` +
        `</div>`
      );
    })
    .join('');
  return (
    `<div style="min-width:180px;font-size:14px;line-height:1.5">` +
    `<div style="font-weight:600;font-size:13.6px;color:${chartColors.text};margin-bottom:6px">${escapeHtml(title)}</div>` +
    `<div style="display:flex;flex-direction:column;gap:4px">${items}</div>` +
    `</div>`
  );
}

/** Base option shared by every chart: font, no animation, styled axis tooltip. */
export function baseOption({ axisPointer, formatter }) {
  return {
    animation: false,
    textStyle: { fontFamily: FONT_FAMILY },
    tooltip: {
      trigger: 'axis',
      axisPointer,
      formatter,
      backgroundColor: '#ffffff',
      borderColor: '#dfe4ec',
      borderWidth: 1,
      padding: [10, 12],
      extraCssText: 'box-shadow:0 8px 24px rgba(15,30,60,0.12);border-radius:8px;',
      confine: true,
    },
  };
}

export const shadowPointer = { type: 'shadow', shadowStyle: { color: 'rgba(31,95,214,0.06)' } };
export const linePointer = { type: 'line', lineStyle: { color: chartColors.axis, type: [3, 3] } };

/** Value axis with compact numbers ("1.2M") and a light grid. */
export const valueAxis = {
  type: 'value',
  axisLabel: { color: chartColors.axis, fontSize: 12, formatter: (v) => formatNumber(v, { compact: true }) },
  axisLine: { show: false },
  axisTick: { show: false },
  splitLine: { lineStyle: { color: chartColors.grid } },
};
