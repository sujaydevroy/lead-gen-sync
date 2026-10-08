'use client';

import { ThemeProvider } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import theme from '@/lib/theme';
import StoreProvider from '@/store/StoreProvider';
import { AuthProvider } from './AuthProvider';
import { NotificationProvider } from './NotificationProvider';
import SettingsSync from './SettingsSync';

export default function AppProviders({ children }) {
  return (
    <StoreProvider>
      <ThemeProvider theme={theme}>
        <CssBaseline />
        <NotificationProvider>
          <AuthProvider>
            <SettingsSync />
            {children}
          </AuthProvider>
        </NotificationProvider>
      </ThemeProvider>
    </StoreProvider>
  );
}
