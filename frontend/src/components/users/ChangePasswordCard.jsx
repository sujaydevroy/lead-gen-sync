'use client';

import { useState } from 'react';
import { useForm } from 'react-hook-form';
import Stack from '@mui/material/Stack';
import TextField from '@mui/material/TextField';
import Button from '@mui/material/Button';
import Alert from '@mui/material/Alert';
import CircularProgress from '@mui/material/CircularProgress';
import SectionCard from '@/components/ui/SectionCard';
import { useNotify } from '@/components/providers/NotificationProvider';
import authService from '@/services/authService';

const EMPTY = { currentPassword: '', newPassword: '', confirmPassword: '' };

/** Change your own password (e.g. the temporary one an administrator gave you). */
export default function ChangePasswordCard() {
  const notify = useNotify();
  const [serverError, setServerError] = useState('');
  const {
    register,
    handleSubmit,
    reset,
    getValues,
    formState: { errors, isSubmitting },
  } = useForm({ defaultValues: EMPTY });

  const onSubmit = async (values) => {
    setServerError('');
    try {
      await authService.changePassword(values.currentPassword, values.newPassword);
      reset(EMPTY);
      notify('Password changed', 'success');
    } catch (error) {
      setServerError(error.message);
    }
  };

  const field = (name, label, rules, autoComplete) => (
    <TextField
      fullWidth
      type="password"
      label={label}
      autoComplete={autoComplete}
      error={Boolean(errors[name])}
      helperText={errors[name]?.message}
      {...register(name, rules)}
    />
  );

  return (
    <SectionCard title="Change password" subtitle="Use at least 8 characters">
      <Stack component="form" spacing={2} onSubmit={handleSubmit(onSubmit)} noValidate>
        {serverError && <Alert severity="error">{serverError}</Alert>}
        {field('currentPassword', 'Current password', { required: 'Enter your current password' }, 'current-password')}
        {field(
          'newPassword',
          'New password',
          { required: 'Enter a new password', minLength: { value: 8, message: 'Use at least 8 characters' } },
          'new-password',
        )}
        {field(
          'confirmPassword',
          'Repeat new password',
          { validate: (v) => v === getValues('newPassword') || 'The passwords do not match' },
          'new-password',
        )}
        <Stack direction="row" sx={{ justifyContent: 'flex-end' }}>
          <Button
            type="submit"
            variant="contained"
            disabled={isSubmitting}
            startIcon={isSubmitting ? <CircularProgress size={16} color="inherit" /> : null}
          >
            {isSubmitting ? 'Saving…' : 'Change password'}
          </Button>
        </Stack>
      </Stack>
    </SectionCard>
  );
}
