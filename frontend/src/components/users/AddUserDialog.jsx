'use client';

import { useState } from 'react';
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
import companyUserService from '@/services/companyUserService';

const EMPTY = { name: '', email: '', jobTitle: '', phone: '', role: 'Viewer', password: '' };

/**
 * Add a user with a temporary password. `onCreate(values)` saves it (default: the Company Administrator's own
 * company; the System Administrator passes one that adds to the company being viewed).
 */
export default function AddUserDialog({ open, roles, onClose, onCreated, onCreate = companyUserService.createUser }) {
  const [serverError, setServerError] = useState('');
  const {
    register,
    control,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm({ defaultValues: EMPTY });

  const close = () => {
    if (isSubmitting) return;
    reset(EMPTY);
    setServerError('');
    onClose();
  };

  const onSubmit = async (values) => {
    setServerError('');
    try {
      const user = await onCreate({
        name: values.name.trim(),
        email: values.email.trim(),
        jobTitle: values.jobTitle.trim() || null,
        phone: values.phone.trim() || null,
        role: values.role,
        password: values.password,
      });
      reset(EMPTY);
      onCreated(user);
    } catch (error) {
      setServerError(error.message);
    }
  };

  const field = (name, label, rules, props = {}) => (
    <TextField fullWidth label={label} error={Boolean(errors[name])} helperText={errors[name]?.message} {...register(name, rules)} {...props} />
  );

  return (
    <Dialog open={open} onClose={close} maxWidth="sm" fullWidth>
      <DialogTitle>Add user</DialogTitle>
      <DialogContent dividers>
        <Stack component="form" id="add-user-form" spacing={2.25} onSubmit={handleSubmit(onSubmit)} noValidate>
          {serverError && <Alert severity="error">{serverError}</Alert>}
          {field('name', 'Full name *', {
            required: 'Name is required',
            validate: (v) => v.trim().length >= 2 || 'Use at least 2 characters',
          })}
          {field(
            'email',
            'Email *',
            { required: 'Email is required', pattern: { value: EMAIL_PATTERN, message: 'Enter a valid email address' } },
            { type: 'email' },
          )}
          <Controller
            name="role"
            control={control}
            render={({ field: roleField }) => (
              <TextField select fullWidth label="Role *" {...roleField}>
                {roles.map((role) => (
                  <MenuItem key={role} value={role}>
                    {role}
                  </MenuItem>
                ))}
              </TextField>
            )}
          />
          {field('jobTitle', 'Job title', { maxLength: { value: 80, message: 'Use 80 characters or fewer' } })}
          {field('phone', 'Phone', { pattern: { value: /^[+()\d\s-]{7,20}$/, message: 'Enter a valid phone number' } })}
          {field(
            'password',
            'Temporary password *',
            { required: 'Password is required', minLength: { value: 8, message: 'Use at least 8 characters' } },
            {
              type: 'password',
              autoComplete: 'new-password',
              helperText: errors.password?.message || 'Share it with the user; they can change it under My Profile.',
            },
          )}
        </Stack>
      </DialogContent>
      <DialogActions>
        <Button color="inherit" onClick={close} disabled={isSubmitting}>
          Cancel
        </Button>
        <Button
          type="submit"
          form="add-user-form"
          variant="contained"
          disabled={isSubmitting}
          startIcon={isSubmitting ? <CircularProgress size={16} color="inherit" /> : null}
        >
          {isSubmitting ? 'Adding…' : 'Add user'}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
