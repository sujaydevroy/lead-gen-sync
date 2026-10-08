'use client';

import { useEffect } from 'react';
import { usePathname, useRouter } from 'next/navigation';
import Card from '@mui/material/Card';
import LockOutlinedIcon from '@mui/icons-material/LockOutlined';
import { useAuth } from '@/components/providers/AuthProvider';
import EmptyState from '@/components/ui/EmptyState';
import FullPageLoader from '@/components/ui/FullPageLoader';
import { canOpenPath, homePathFor, isSystemAdmin } from '@/lib/roles';

/**
 * Role-based page access (the API enforces the same rules). System administrators only use the
 * administration pages and are sent there; other users see a "no access" message on admin pages.
 */
export default function RoleGate({ children }) {
  const { user } = useAuth();
  const pathname = usePathname();
  const router = useRouter();
  const allowed = canOpenPath(user, pathname);
  const redirect = !allowed && isSystemAdmin(user);

  useEffect(() => {
    if (redirect) router.replace(homePathFor(user));
  }, [redirect, router, user]);

  if (allowed) return children;
  if (redirect) return <FullPageLoader label="Opening administration…" />;
  return (
    <Card>
      <EmptyState
        icon={<LockOutlinedIcon />}
        title="You don't have access to this page"
        description="Your role cannot open this page. Ask your company administrator if you need access."
        actionLabel="Go to the home page"
        onAction={() => router.push(homePathFor(user))}
      />
    </Card>
  );
}
