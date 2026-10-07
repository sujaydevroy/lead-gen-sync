import { Suspense } from 'react';
import Box from '@mui/material/Box';
import Stack from '@mui/material/Stack';
import Paper from '@mui/material/Paper';
import Typography from '@mui/material/Typography';
import CheckCircleOutlineRoundedIcon from '@mui/icons-material/CheckCircleOutlineRounded';
import LoginForm from '@/components/auth/LoginForm';
import BrandMark from '@/components/layout/BrandMark';

export const metadata = { title: 'Login' };

const HIGHLIGHTS = [
  'Find dealers by country, region, sector and status',
  'Message, email or call dealers from one place',
  'Keep a complete communication history per dealer',
  'Upload sales data and forecast the next 12 months',
];

export default function LoginPage() {
  return (
    <Box sx={{ minHeight: '100vh', display: 'grid', gridTemplateColumns: { xs: '1fr', md: '1.05fr 1fr' } }}>
      <Box
        sx={{
          display: { xs: 'none', md: 'flex' },
          flexDirection: 'column',
          justifyContent: 'space-between',
          p: 6,
          color: '#fff',
          background: 'linear-gradient(150deg, #0f1e3c 0%, #173a7a 60%, #1f5fd6 100%)',
        }}
      >
        <BrandMark inverted />
        <Box sx={{ maxWidth: 460 }}>
          <Typography variant="h4" sx={{ color: '#fff', fontSize: '2.1rem', lineHeight: 1.2 }}>
            Connect with your dealer network, everywhere you sell.
          </Typography>
          <Stack spacing={1.5} sx={{ mt: 4 }}>
            {HIGHLIGHTS.map((text) => (
              <Stack key={text} direction="row" spacing={1.5} sx={{ alignItems: 'center' }}>
                <CheckCircleOutlineRoundedIcon sx={{ color: '#8fb4ff' }} fontSize="small" />
                <Typography sx={{ color: 'rgba(255,255,255,0.88)' }}>{text}</Typography>
              </Stack>
            ))}
          </Stack>
        </Box>
        <Typography variant="body2" sx={{ color: 'rgba(255,255,255,0.6)' }}>
          © {new Date().getFullYear()} ABC Corporation · Secure company access
        </Typography>
      </Box>

      <Box sx={{ display: 'grid', placeItems: 'center', p: { xs: 2, sm: 4 }, bgcolor: 'background.default' }}>
        <Paper variant="outlined" sx={{ width: '100%', maxWidth: 440, p: { xs: 3, sm: 4.5 }, borderRadius: 3 }}>
          <Box sx={{ mb: 3 }}>
            <BrandMark />
          </Box>
          <Typography variant="h5" component="h1">
            Welcome back
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5, mb: 3 }}>
            Sign in with your company account to manage dealer communication.
          </Typography>
          <Suspense fallback={null}>
            <LoginForm />
          </Suspense>
        </Paper>
      </Box>
    </Box>
  );
}
