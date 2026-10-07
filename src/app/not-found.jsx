'use client';

import Link from 'next/link';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Typography from '@mui/material/Typography';

export default function NotFound() {
  return (
    <Box sx={{ minHeight: '100vh', display: 'grid', placeItems: 'center', p: 3, textAlign: 'center' }}>
      <Box>
        <Typography variant="overline">Error 404</Typography>
        <Typography variant="h4" component="h1" sx={{ mt: 1 }}>
          Page not found
        </Typography>
        <Typography color="text.secondary" sx={{ mt: 1, mb: 3 }}>
          The page you are looking for does not exist or has moved.
        </Typography>
        <Button component={Link} href="/dealers" variant="contained">
          Go to Dealers
        </Button>
      </Box>
    </Box>
  );
}
