'use client';

import { useEffect, useState } from 'react';
import Dialog from '@mui/material/Dialog';
import DialogTitle from '@mui/material/DialogTitle';
import DialogContent from '@mui/material/DialogContent';
import DialogContentText from '@mui/material/DialogContentText';
import DialogActions from '@mui/material/DialogActions';
import Button from '@mui/material/Button';
import TextField from '@mui/material/TextField';
import Alert from '@mui/material/Alert';

/** Set a temporary password for a user. `onSave(password)` returns the updated user. */
export default function SetPasswordDialog({ user, onClose, onSave, onSaved }) {
  const [password, setPassword] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    setPassword('');
    setError('');
  }, [user]);

  const save = async () => {
    setSaving(true);
    setError('');
    try {
      onSaved(await onSave(password));
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog open={Boolean(user)} onClose={() => !saving && onClose()} maxWidth="xs" fullWidth>
      <DialogTitle>Set a temporary password</DialogTitle>
      <DialogContent>
        <DialogContentText sx={{ mb: 2 }}>
          {user?.name} is signed out everywhere and signs in with this password. They can change it under My Profile.
        </DialogContentText>
        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}
        <TextField
          autoFocus
          fullWidth
          type="password"
          label="Temporary password"
          autoComplete="new-password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          helperText="At least 8 characters"
        />
      </DialogContent>
      <DialogActions>
        <Button color="inherit" onClick={onClose} disabled={saving}>
          Cancel
        </Button>
        <Button variant="contained" onClick={save} disabled={password.length < 8 || saving}>
          {saving ? 'Saving…' : 'Set password'}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
