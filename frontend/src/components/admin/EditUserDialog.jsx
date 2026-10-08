'use client';

import { useEffect, useState } from 'react';
import { Controller, useForm } from 'react-hook-form';
import Dialog from '@mui/material/Dialog';
import DialogTitle from '@mui/material/DialogTitle';
import DialogContent from '@mui/material/DialogContent';
import DialogActions from '@mui/material/DialogActions';
import Button from '@mui/material/Button';
import Stack from '@mui/material/Stack';
import TextField from '@mui/material/TextField';
import MenuItem from '@mui/material/MenuItem';
import Alert from '@mui/material/Alert';
import CircularProgress from '@mui/material/CircularProgress';
import { EMAIL_PATTERN } from '@/components/auth/validation';

const toForm = (user) => ({
  name: user?.name || '',
  email: user?.email || '',
  jobTitle: user?.jobTitle || '',
  phone: user?.phone || '',
  role: user?.role || '',
});

/** System administrators edit a company user's details and role. `onSave(changes)` returns the updated user. */
export default function EditUserDialog({ user, roles, onClose, onSave, onSaved }) {
  const [serverError, setServerError] = useState('');
  const {
    register,
    control,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting, isDirty },
  } = useForm({ defaultValues: toForm(user) });

  useEffect(() => {
    if (user) {
      reset(toForm(user));
      setServerError('');
    }
  }, [user, reset]);

  const onSubmit = async (values) => {
    setServerError('');
    try {
      const updated = await onSave({
        name: values.name.trim(),
        email: values.email.trim(),
        jobTitle: values.jobTitle.trim() || null,
        phone: values.phone.trim() || null,
        role: values.role,
      });
      onSaved(updated);
    } catch (error) {
      setServerError(error.message);
    }
  };

  const field = (name, label, rules, props = {}) => (
    <TextField fullWidth label={label} error={Boolean(errors[name])} helperText={errors[name]?.message} {...register(name, rules)} {...props} />
  );
  const roleOptions = user && !roles.includes(user.role) ? [user.role, ...roles] : roles;

  return (
    <Dialog open={Boolean(user)} onClose={() => !isSubmitting && onClose()} maxWidth="sm" fullWidth>
      <DialogTitle>Edit user {user ? `· ${user.id}` : ''}</DialogTitle>
      <DialogContent dividers>
        <Stack component="form" id="edit-user-form" spacing={2.25} onSubmit={handleSubmit(onSubmit)} noValidate>
          {serverError && <Alert severity="error">{serverError}</Alert>}
          {field('name', 'Full name *', {
            required: 'Name is required',
            validate: (v) => v.trim().length >= 2 || 'Use at least 2 characters',
          })}
          {field(
            'email',
            'Email *',
            { required: 'Email is required', pattern: { value: EMAIL_PATTERN, message: 'Enter a valid email address' } },
            { type: 'email', helperText: errors.email?.message || 'The user signs in with this email' },
          )}
          <Controller
            name="role"
            control={control}
            render={({ field: roleField }) => (
              <TextField select fullWidth label="Role *" {...roleField}>
                {roleOptions.map((role) => (
                  <MenuItem key={role} value={role}>
                    {role}
                  </MenuItem>
                ))}
              </TextField>
            )}
          />
          {field('jobTitle', 'Job title', { maxLength: { value: 80, message: 'Use 80 characters or fewer' } })}
          {field('phone', 'Phone', { pattern: { value: /^[+()\d\s-]{7,20}$/, message: 'Enter a valid phone number' } })}
        </Stack>
      </DialogContent>
      <DialogActions>
        <Button color="inherit" onClick={onClose} disabled={isSubmitting}>
          Cancel
        </Button>
        <Button
          type="submit"
          form="edit-user-form"
          variant="contained"
          disabled={!isDirty || isSubmitting}
          startIcon={isSubmitting ? <CircularProgress size={16} color="inherit" /> : null}
        >
          {isSubmitting ? 'Saving…' : 'Save changes'}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
