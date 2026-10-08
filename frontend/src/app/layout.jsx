import { AppRouterCacheProvider } from '@mui/material-nextjs/v16-appRouter';
import AppProviders from '@/components/providers/AppProviders';
import '@/styles/globals.css';

export const metadata = {
  title: {
    default: 'Dealer Communication Portal',
    template: '%s · Dealer Communication Portal',
  },
  description: 'Find dealers by country and region and communicate with them.',
};

export const viewport = {
  width: 'device-width',
  initialScale: 1,
  themeColor: '#1f5fd6',
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>
        <AppRouterCacheProvider options={{ key: 'mui' }}>
          <AppProviders>{children}</AppProviders>
        </AppRouterCacheProvider>
      </body>
    </html>
  );
}
