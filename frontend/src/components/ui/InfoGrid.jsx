import Grid from '@mui/material/Grid';
import Typography from '@mui/material/Typography';
import { displayValue } from '@/lib/format';

/**
 * Label / value pairs in a responsive grid.
 * @param {{ items: { label: string, value: React.ReactNode, full?: boolean }[], columns?: number }} props
 */
export default function InfoGrid({ items, columns = 2 }) {
  return (
    <Grid container spacing={2.5}>
      {items.map(({ label, value, full }) => (
        <Grid key={label} size={{ xs: 12, sm: full ? 12 : 12 / columns }}>
          <Typography variant="caption" component="div" sx={{ textTransform: 'uppercase', letterSpacing: '0.05em', fontWeight: 600 }}>
            {label}
          </Typography>
          <Typography variant="body2" component="div" sx={{ mt: 0.5, fontWeight: 500, wordBreak: 'break-word' }}>
            {typeof value === 'string' || value === undefined || value === null ? displayValue(value) : value}
          </Typography>
        </Grid>
      ))}
    </Grid>
  );
}
