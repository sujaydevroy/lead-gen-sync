import { hasValue, NOT_AVAILABLE } from '@/types/dealer';

const MONTHS_SHORT = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

export function formatDate(value, { withTime = false } = {}) {
  if (!hasValue(value)) return NOT_AVAILABLE;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  const datePart = `${MONTHS_SHORT[date.getMonth()]} ${String(date.getDate()).padStart(2, '0')}, ${date.getFullYear()}`;
  if (!withTime) return datePart;
  const time = date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
  return `${datePart} · ${time}`;
}

export function formatRelativeTime(value, now = Date.now()) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '';
  const diff = Math.max(0, now - date.getTime());
  const minutes = Math.floor(diff / 60000);
  if (minutes < 1) return 'Just now';
  if (minutes < 60) return `${minutes} minute${minutes === 1 ? '' : 's'} ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours} hour${hours === 1 ? '' : 's'} ago`;
  const days = Math.floor(hours / 24);
  if (days === 1) return 'Yesterday';
  if (days < 30) return `${days} days ago`;
  return formatDate(value);
}

/** "2025-03" -> "Mar 2025" */
export function formatPeriod(period) {
  if (!period) return '';
  const [year, month] = period.split('-').map(Number);
  return `${MONTHS_SHORT[month - 1]} ${year}`;
}

/** "2025-03" -> "Mar '25" (compact axis label) */
export function formatPeriodShort(period) {
  if (!period) return '';
  const [year, month] = period.split('-').map(Number);
  return `${MONTHS_SHORT[month - 1]} '${String(year).slice(2)}`;
}

export function formatCurrency(value, currency = 'USD', { compact = false } = {}) {
  if (value === null || value === undefined || Number.isNaN(value)) return '—';
  try {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency,
      notation: compact ? 'compact' : 'standard',
      maximumFractionDigits: compact ? 1 : 0,
    }).format(value);
  } catch {
    // Unknown ISO code: fall back to number + code
    return `${formatNumber(value, { compact })} ${currency}`;
  }
}

export function formatNumber(value, { compact = false, decimals = 0 } = {}) {
  if (value === null || value === undefined || Number.isNaN(value)) return '—';
  return new Intl.NumberFormat('en-US', {
    notation: compact ? 'compact' : 'standard',
    maximumFractionDigits: compact ? 1 : decimals,
  }).format(value);
}

export function formatPercent(value, { decimals = 1, signed = false } = {}) {
  if (value === null || value === undefined || !Number.isFinite(value)) return '—';
  const sign = signed && value > 0 ? '+' : '';
  return `${sign}${value.toFixed(decimals)}%`;
}

export function formatFileSize(bytes) {
  if (!bytes && bytes !== 0) return '';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function initials(name = '') {
  return name
    .replace(/[^A-Za-z0-9 ]/g, ' ')
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0].toUpperCase())
    .join('');
}

export function displayValue(value) {
  return hasValue(value) ? value : NOT_AVAILABLE;
}
