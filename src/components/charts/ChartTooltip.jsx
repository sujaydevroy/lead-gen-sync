import Paper from '@mui/material/Paper';
import Typography from '@mui/material/Typography';
import Stack from '@mui/material/Stack';
import Box from '@mui/material/Box';

/** Shared tooltip card for Recharts charts. `rows` = [{ label, value, color?, dashed? }] */
export default function ChartTooltip({ title, rows }) {
  return (
    <Paper variant="outlined" sx={{ px: 1.5, py: 1.25, boxShadow: '0 8px 24px rgba(15,30,60,0.12)', minWidth: 180, pointerEvents: 'none' }}>
      <Typography variant="subtitle2" sx={{ mb: 0.75 }}>
        {title}
      </Typography>
      <Stack spacing={0.5}>
        {rows.map(({ label, value, color, dashed }) => (
          <Stack key={label} direction="row" spacing={2} sx={{ justifyContent: 'space-between', alignItems: 'center' }}>
            <Stack direction="row" spacing={0.75} sx={{ alignItems: 'center' }}>
              {color && (
                <Box
                  aria-hidden
                  sx={{ width: 12, height: 0, borderTop: `2px ${dashed ? 'dashed' : 'solid'} ${color}` }}
                />
              )}
              <Typography variant="body2" color="text.secondary">
                {label}
              </Typography>
            </Stack>
            <Typography variant="body2" sx={{ fontWeight: 600, fontVariantNumeric: 'tabular-nums' }}>
              {value}
            </Typography>
          </Stack>
        ))}
      </Stack>
    </Paper>
  );
}
