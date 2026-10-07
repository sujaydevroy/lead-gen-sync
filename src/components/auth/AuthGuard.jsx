'use client';

import { useEffect } from 'react';
import { usePathname, useRouter } from 'next/navigation';
import { useAuth } from '@/components/providers/AuthProvider';
import FullPageLoader from '@/components/ui/FullPageLoader';

/**
 * Client-side route protection. proxy.js already redirects requests without a valid
 * session cookie; this guard covers sessions that expire while the app is open.
 */
export default function AuthGuard({ children }) {
  const { status, user } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (status === 'unauthenticated') {
      router.replace(`/login?next=${encodeURIComponent(pathname)}`);
    }
  }, [status, router, pathname]);

  if (!user) return <FullPageLoader label={status === 'unauthenticated' ? 'Redirecting to login…' : 'Loading your workspace…'} />;
  return children;
}
