'use client';

import { useState } from 'react';
import Card from '@mui/material/Card';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Skeleton from '@mui/material/Skeleton';
import Dialog from '@mui/material/Dialog';
import DialogTitle from '@mui/material/DialogTitle';
import DialogContent from '@mui/material/DialogContent';
import DialogContentText from '@mui/material/DialogContentText';
import DialogActions from '@mui/material/DialogActions';
import PersonAddAlt1RoundedIcon from '@mui/icons-material/PersonAddAlt1Rounded';
import PageHeader from '@/components/ui/PageHeader';
import EmptyState from '@/components/ui/EmptyState';
import UserTable from '@/components/admin/UserTable';
import EditUserDialog from '@/components/admin/EditUserDialog';
import AddUserDialog from '@/components/users/AddUserDialog';
import SetPasswordDialog from '@/components/users/SetPasswordDialog';
import { useAuth } from '@/components/providers/AuthProvider';
import { useNotify } from '@/components/providers/NotificationProvider';
import useAsync from '@/hooks/useAsync';
import companyUserService from '@/services/companyUserService';

export default function UsersPage() {
  const { user: me, company } = useAuth();
  const notify = useNotify();
  const { data: users, loading, error, reload } = useAsync(() => companyUserService.listUsers(), []);
  const { data: roles } = useAsync(() => companyUserService.listRoles(), []);
  const [list, setList] = useState(null);
  const [busyId, setBusyId] = useState(null);
  const [adding, setAdding] = useState(false);
  const [passwordFor, setPasswordFor] = useState(null);
  const [deactivating, setDeactivating] = useState(null);
  const [editing, setEditing] = useState(null);

  const rows = list ?? users;
  const replace = (updated) => setList((rows ?? []).map((u) => (u.id === updated.id ? updated : u)));

  const run = async (user, action, message) => {
    setBusyId(user.id);
    try {
      const updated = await action();
      replace(updated);
      notify(message(updated), 'success');
      return true;
    } catch (err) {
      notify(err.message, 'error');
      return false;
    } finally {
      setBusyId(null);
    }
  };

  const changeRole = (user, role) =>
    run(user, () => companyUserService.updateUser(user.id, { role }), (u) => `${u.name} is now ${u.role}`);

  const setActive = (user, isActive) =>
    run(
      user,
      () => companyUserService.updateUser(user.id, { isActive }),
      (u) => (u.isActive ? `${u.name} was activated` : `${u.name} was deactivated and signed out`),
    );

  return (
    <>
      <PageHeader
        title="Users"
        subtitle={`People who can sign in to ${company?.name || 'your company'}`}
        actions={
          <Button variant="contained" startIcon={<PersonAddAlt1RoundedIcon />} onClick={() => setAdding(true)} disabled={!roles}>
            Add user
          </Button>
        }
      />
      <Card>
        {error ? (
          <EmptyState variant="error" title="Users could not be loaded" description={error.message} actionLabel="Retry" onAction={reload} />
        ) : loading && !rows ? (
          <Box sx={{ p: 2 }}>
            {[0, 1, 2].map((i) => (
              <Skeleton key={i} height={52} />
            ))}
          </Box>
        ) : (
          <UserTable
            users={rows}
            manage
            roles={roles || []}
            currentUserId={me.id}
            busyId={busyId}
            onChangeRole={changeRole}
            onToggleActive={(user, active) => (active ? setActive(user, true) : setDeactivating(user))}
            onEdit={setEditing}
            onUnlock={(user) => run(user, () => companyUserService.unlockUser(user.id), (u) => `${u.name} was unlocked`)}
            onSetPassword={setPasswordFor}
          />
        )}
      </Card>

      <AddUserDialog
        open={adding}
        roles={roles || []}
        onClose={() => setAdding(false)}
        onCreated={(user) => {
          setAdding(false);
          setList([...(rows ?? []), user].sort((a, b) => a.name.localeCompare(b.name)));
          notify(`${user.name} was added`, 'success');
        }}
      />

      <Dialog open={Boolean(deactivating)} onClose={() => setDeactivating(null)}>
        <DialogTitle>Deactivate {deactivating?.name}?</DialogTitle>
        <DialogContent>
          <DialogContentText>
            They are signed out and can no longer sign in. Their messages and history are kept, and you can activate them
            again at any time.
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button color="inherit" onClick={() => setDeactivating(null)}>
            Cancel
          </Button>
          <Button
            color="error"
            variant="contained"
            onClick={() => {
              setActive(deactivating, false);
              setDeactivating(null);
            }}
          >
            Deactivate
          </Button>
        </DialogActions>
      </Dialog>

      <EditUserDialog
        user={editing}
        roles={roles || []}
        lockRole={editing?.id === me.id}
        onClose={() => setEditing(null)}
        onSave={(changes) => companyUserService.updateUser(editing.id, changes)}
        onSaved={(updated) => {
          replace(updated);
          setEditing(null);
          notify(`${updated.name} was updated`, 'success');
        }}
      />

      <SetPasswordDialog
        user={passwordFor}
        onClose={() => setPasswordFor(null)}
        onSave={(password) => companyUserService.setPassword(passwordFor.id, password)}
        onSaved={(updated) => {
          replace(updated);
          setPasswordFor(null);
          notify(`Temporary password set for ${updated.name}`, 'success');
        }}
      />
    </>
  );
}
