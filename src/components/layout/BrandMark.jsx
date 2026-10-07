import Box from '@mui/material/Box';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';
import HubRoundedIcon from '@mui/icons-material/HubRounded';

export const APP_NAME = 'DealerConnect';
export const APP_TAGLINE = 'Dealer Communication Portal';

export default function BrandMark({ inverted = false, compact = false }) {
  return (
    <Stack direction="row" spacing={1.25} sx={{ alignItems: 'center' }}>
      <Box
        sx={{
          width: 36,
          height: 36,
          borderRadius: 2,
          display: 'grid',
          placeItems: 'center',
          bgcolor: inverted ? 'rgba(255,255,255,0.14)' : 'primary.main',
          color: '#fff',
          flexShrink: 0,
        }}
      >
        <HubRoundedIcon fontSize="small" />
      </Box>
      {!compact && (
        <Box sx={{ lineHeight: 1.1 }}>
          <Typography sx={{ fontWeight: 750, fontSize: '1.05rem', color: inverted ? '#fff' : 'text.primary', lineHeight: 1.2 }}>
            {APP_NAME}
          </Typography>
          <Typography sx={{ fontSize: '0.72rem', color: inverted ? 'rgba(255,255,255,0.7)' : 'text.secondary', lineHeight: 1.2 }}>
            {APP_TAGLINE}
          </Typography>
        </Box>
      )}
    </Stack>
  );
}
