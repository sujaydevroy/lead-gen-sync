'use client';

import Stack from '@mui/material/Stack';
import Button from '@mui/material/Button';
import Chip from '@mui/material/Chip';
import Typography from '@mui/material/Typography';
import EditRoundedIcon from '@mui/icons-material/EditRounded';
import LockOpenRoundedIcon from '@mui/icons-material/LockOpenRounded';
import PasswordRoundedIcon from '@mui/icons-material/PasswordRounded';
import SectionCard from '@/components/ui/SectionCard';
import InfoGrid from '@/components/ui/InfoGrid';
import { formatDate } from '@/lib/format';

/** The company's one user (demo 1:1 mapping) with edit, unlock and temporary-password actions. */
export default function CompanyUserCard({ user, busy, onEdit, onUnlock, onSetPassword }) {
  return (
    <SectionCard
      title="User"
      subtitle="The login for this company"
      actions={
        user && (
          <Stack direction="row" spacing={1} sx={{ flexWrap: 'wrap', rowGap: 1 }}>
            <Button size="small" variant="outlined" startIcon={<EditRoundedIcon />} onClick={() => onEdit(user)} disabled={busy}>
              Edit
            </Button>
            {user.isLocked && (
              <Button size="small" variant="outlined" startIcon={<LockOpenRoundedIcon />} onClick={() => onUnlock(user)} disabled={busy}>
                Unlock
              </Button>
            )}
            <Button size="small" variant="outlined" startIcon={<PasswordRoundedIcon />} onClick={() => onSetPassword(user)} disabled={busy}>
              Set password
            </Button>
          </Stack>
        )
      }
    >
      {user ? (
        <InfoGrid
          columns={3}
          items={[
            { label: 'Name', value: user.name },
            { label: 'Email (sign-in)', value: user.email },
            { label: 'Role', value: user.role },
            { label: 'Job title', value: user.jobTitle || '—' },
            { label: 'Phone', value: user.phone || '—' },
            { label: 'User ID', value: user.id },
            {
              label: 'Status',
              value: (
                <Stack direction="row" spacing={0.75}>
                  <Chip size="small" label={user.isActive ? 'Active' : 'Inactive'} color={user.isActive ? 'success' : 'default'} variant="outlined" />
                  {user.isLocked && <Chip size="small" color="warning" variant="outlined" label="Locked" />}
                </Stack>
              ),
            },
            { label: 'Last sign-in', value: user.lastLoginOn ? formatDate(user.lastLoginOn, { withTime: true }) : 'Never' },
            { label: 'Created', value: formatDate(user.createdOn) },
          ]}
        />
      ) : (
        <Typography variant="body2" color="text.secondary">
          This company has no user yet.
        </Typography>
      )}
    </SectionCard>
  );
}
