'use client';

import Table from '@mui/material/Table';
import TableBody from '@mui/material/TableBody';
import TableCell from '@mui/material/TableCell';
import TableContainer from '@mui/material/TableContainer';
import TableHead from '@mui/material/TableHead';
import TableRow from '@mui/material/TableRow';
import Typography from '@mui/material/Typography';
import Stack from '@mui/material/Stack';
import Chip from '@mui/material/Chip';
import TextField from '@mui/material/TextField';
import MenuItem from '@mui/material/MenuItem';
import Switch from '@mui/material/Switch';
import Tooltip from '@mui/material/Tooltip';
import IconButton from '@mui/material/IconButton';
import LockOpenRoundedIcon from '@mui/icons-material/LockOpenRounded';
import PasswordRoundedIcon from '@mui/icons-material/PasswordRounded';
import { formatDate } from '@/lib/format';

function StatusChips({ user }) {
  return (
    <Stack direction="row" spacing={0.75}>
      <Chip
        size="small"
        label={user.isActive ? 'Active' : 'Inactive'}
        sx={user.isActive ? { bgcolor: '#e6f5ee', color: '#1e7a4f', fontWeight: 600 } : { bgcolor: '#eef1f5', color: '#52607a', fontWeight: 600 }}
      />
      {user.isLocked && <Chip size="small" color="warning" variant="outlined" label="Locked" />}
    </Stack>
  );
}

/**
 * Users of one company. Read-only for system administrators; with `manage`, a Company Administrator
 * changes roles, activates / deactivates, unlocks and sets temporary passwords.
 */
export default function UserTable({ users, manage = false, roles = [], currentUserId, busyId, onChangeRole, onToggleActive, onUnlock, onSetPassword }) {
  if (!users.length) {
    return (
      <Typography variant="body2" color="text.secondary" sx={{ p: 2.5 }}>
        No users yet.
      </Typography>
    );
  }
  return (
    <TableContainer>
      <Table size="small" aria-label="Users">
        <TableHead>
          <TableRow>
            <TableCell>Name</TableCell>
            <TableCell>Email</TableCell>
            <TableCell>Role</TableCell>
            <TableCell>Status</TableCell>
            <TableCell>Last sign-in</TableCell>
            {manage && <TableCell align="right">Actions</TableCell>}
          </TableRow>
        </TableHead>
        <TableBody>
          {users.map((user) => {
            const self = user.id === currentUserId;
            const busy = busyId === user.id;
            return (
              <TableRow key={user.id} hover sx={{ opacity: user.isActive ? 1 : 0.65 }}>
                <TableCell>
                  <Typography variant="subtitle2">
                    {user.name}
                    {self && (
                      <Typography component="span" variant="caption" color="text.secondary">
                        {' '}
                        (you)
                      </Typography>
                    )}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    {[user.id, user.jobTitle].filter(Boolean).join(' · ')}
                  </Typography>
                </TableCell>
                <TableCell sx={{ wordBreak: 'break-all' }}>{user.email}</TableCell>
                <TableCell sx={{ minWidth: manage ? 200 : undefined }}>
                  {manage ? (
                    <TextField
                      select
                      size="small"
                      fullWidth
                      value={user.role}
                      disabled={self || busy}
                      onChange={(e) => onChangeRole(user, e.target.value)}
                      slotProps={{ htmlInput: { 'aria-label': `Role of ${user.name}` } }}
                    >
                      {(roles.includes(user.role) ? roles : [user.role, ...roles]).map((role) => (
                        <MenuItem key={role} value={role}>
                          {role}
                        </MenuItem>
                      ))}
                    </TextField>
                  ) : (
                    user.role
                  )}
                </TableCell>
                <TableCell>
                  <StatusChips user={user} />
                </TableCell>
                <TableCell>{user.lastLoginOn ? formatDate(user.lastLoginOn, { withTime: true }) : 'Never'}</TableCell>
                {manage && (
                  <TableCell align="right" sx={{ whiteSpace: 'nowrap' }}>
                    <Tooltip title={self ? 'You cannot deactivate yourself' : user.isActive ? 'Deactivate user' : 'Activate user'}>
                      <span>
                        <Switch
                          checked={user.isActive}
                          disabled={self || busy}
                          onChange={(e) => onToggleActive(user, e.target.checked)}
                          slotProps={{ input: { 'aria-label': `${user.name} active` } }}
                        />
                      </span>
                    </Tooltip>
                    <Tooltip title="Unlock account">
                      <span>
                        <IconButton size="small" disabled={!user.isLocked || busy} onClick={() => onUnlock(user)} aria-label={`Unlock ${user.name}`}>
                          <LockOpenRoundedIcon fontSize="small" />
                        </IconButton>
                      </span>
                    </Tooltip>
                    <Tooltip title="Set a temporary password">
                      <span>
                        <IconButton size="small" disabled={busy} onClick={() => onSetPassword(user)} aria-label={`Set password for ${user.name}`}>
                          <PasswordRoundedIcon fontSize="small" />
                        </IconButton>
                      </span>
                    </Tooltip>
                  </TableCell>
                )}
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
    </TableContainer>
  );
}
