import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import Box from '@mui/material/Box';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';
import Skeleton from '@mui/material/Skeleton';
import Tooltip from '@mui/material/Tooltip';

/** KPI tile: label, headline value and an optional caption / delta. */
export default function StatCard({ label, value, caption, icon, loading = false, tooltip, accent = 'primary.main' }) {
  const content = (
    <Card sx={{ height: '100%' }}>
      <CardContent sx={{ p: 2.25, '&:last-child': { pb: 2.25 } }}>
        <Stack direction="row" spacing={1.5} sx={{ alignItems: 'flex-start', justifyContent: 'space-between' }}>
          <Box sx={{ minWidth: 0 }}>
            <Typography variant="body2" color="text.secondary" sx={{ fontWeight: 500 }}>
              {label}
            </Typography>
            {loading ? (
              <Skeleton width={90} height={40} />
            ) : (
              <Typography
                variant="h5"
                component="p"
                sx={{ mt: 0.5, fontVariantNumeric: 'tabular-nums', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}
              >
                {value}
              </Typography>
            )}
            {caption && !loading && (
              <Typography variant="caption" component="div" sx={{ mt: 0.5 }}>
                {caption}
              </Typography>
            )}
          </Box>
          {icon && (
            <Box
              sx={{
                width: 40,
                height: 40,
                borderRadius: 2,
                display: 'grid',
                placeItems: 'center',
                bgcolor: 'rgba(31,95,214,0.08)',
                color: accent,
                flexShrink: 0,
              }}
            >
              {icon}
            </Box>
          )}
        </Stack>
      </CardContent>
    </Card>
  );
  return tooltip ? (
    <Tooltip title={tooltip} placement="top">
      <Box sx={{ height: '100%' }}>{content}</Box>
    </Tooltip>
  ) : (
    content
  );
}
