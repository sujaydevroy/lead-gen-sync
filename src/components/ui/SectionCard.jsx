import Card from '@mui/material/Card';
import Box from '@mui/material/Box';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';
import Divider from '@mui/material/Divider';

/** Card with a titled header row and optional actions. */
export default function SectionCard({ title, subtitle, actions, children, noPadding = false, sx }) {
  return (
    <Card sx={{ height: '100%', display: 'flex', flexDirection: 'column', ...sx }}>
      {(title || actions) && (
        <>
          <Stack
            direction="row"
            spacing={2}
            sx={{ px: 2.5, py: 2, alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', rowGap: 1 }}
          >
            <Box sx={{ minWidth: 0 }}>
              {title && (
                <Typography variant="h6" component="h2">
                  {title}
                </Typography>
              )}
              {subtitle && (
                <Typography variant="body2" color="text.secondary">
                  {subtitle}
                </Typography>
              )}
            </Box>
            {actions}
          </Stack>
          <Divider />
        </>
      )}
      <Box sx={{ p: noPadding ? 0 : 2.5, flexGrow: 1, minWidth: 0 }}>{children}</Box>
    </Card>
  );
}
