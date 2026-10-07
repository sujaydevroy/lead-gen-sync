import Chip from '@mui/material/Chip';
import Box from '@mui/material/Box';

const STYLES = {
  Active: { color: '#1e7a4f', bg: '#e6f5ee', dot: '#22a06b' },
  Inactive: { color: '#52607a', bg: '#eef1f5', dot: '#8b95a7' },
  Pending: { color: '#8a5a00', bg: '#fdf3e1', dot: '#e2a400' },
};

/** Dealer status pill: green = Active, gray = Inactive, yellow = Pending (always with a text label). */
export default function StatusBadge({ status, size = 'small' }) {
  const style = STYLES[status] || STYLES.Inactive;
  return (
    <Chip
      size={size}
      label={status}
      icon={<Box component="span" sx={{ width: 8, height: 8, borderRadius: '50%', bgcolor: style.dot, ml: '8px !important' }} />}
      sx={{ color: style.color, bgcolor: style.bg, fontWeight: 600, border: 'none' }}
    />
  );
}
