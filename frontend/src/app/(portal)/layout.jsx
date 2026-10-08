import Box from '@mui/material/Box';
import AuthGuard from '@/components/auth/AuthGuard';
import AppHeader from '@/components/layout/AppHeader';
import RoleGate from '@/components/auth/RoleGate';

export default function PortalLayout({ children }) {
  return (
    <AuthGuard>
      <Box sx={{ minHeight: '100vh', bgcolor: 'background.default' }}>
        <AppHeader />
        <Box component="main" sx={{ px: { xs: 2, sm: 3, lg: 4 }, py: { xs: 2.5, md: 3.5 }, maxWidth: 1600, mx: 'auto' }}>
          <RoleGate>{children}</RoleGate>
        </Box>
      </Box>
    </AuthGuard>
  );
}
