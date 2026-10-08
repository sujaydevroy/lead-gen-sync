import { Suspense } from 'react';
import Box from '@mui/material/Box';
import Paper from '@mui/material/Paper';
import Typography from '@mui/material/Typography';
import BrandMark from '@/components/layout/BrandMark';
import ResetPasswordForm from '@/components/auth/ResetPasswordForm';

export const metadata = { title: 'Reset password' };

export default function ResetPasswordPage() {
  return (
    <Box sx={{ minHeight: '100vh', display: 'grid', placeItems: 'center', p: { xs: 2, sm: 4 }, bgcolor: 'background.default' }}>
      <Paper variant="outlined" sx={{ width: '100%', maxWidth: 440, p: { xs: 3, sm: 4.5 }, borderRadius: 3 }}>
        <Box sx={{ mb: 3 }}>
          <BrandMark />
        </Box>
        <Typography variant="h5" component="h1">
          Choose a new password
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5, mb: 3 }}>
          Use at least 8 characters. You&apos;ll be signed out everywhere after the change.
        </Typography>
        <Suspense fallback={null}>
          <ResetPasswordForm />
        </Suspense>
      </Paper>
    </Box>
  );
}
