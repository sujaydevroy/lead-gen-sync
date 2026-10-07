'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useSearchParams } from 'next/navigation';
import { useForm } from 'react-hook-form';
import Stack from '@mui/material/Stack';
import TextField from '@mui/material/TextField';
import Button from '@mui/material/Button';
import Alert from '@mui/material/Alert';
import CircularProgress from '@mui/material/CircularProgress';
import authService from '@/services/authService';

const MIN_LENGTH = 8;

export default function ResetPasswordForm() {
  const token = useSearchParams().get('token') || '';
  const [done, setDone] = useState(false);
  const [serverError, setServerError] = useState('');
  const {
    register,
    handleSubmit,
    getValues,
    formState: { errors, isSubmitting },
  } = useForm({ defaultValues: { password: '', confirm: '' } });

  if (!token) {
    return (
      <Alert severity="error">
        This reset link is incomplete. Request a new one from the <Link href="/login">login page</Link>.
      </Alert>
    );
  }

  if (done) {
    return (
      <Stack spacing={2}>
        <Alert severity="success">Your password has been changed.</Alert>
        <Button component={Link} href="/login" variant="contained">
          Go to login
        </Button>
      </Stack>
    );
  }

  const onSubmit = async ({ password }) => {
    setServerError('');
    try {
      await authService.resetPassword(token, password);
      setDone(true);
    } catch (error) {
      setServerError(error.message);
    }
  };

  return (
    <Stack component="form" spacing={2.25} onSubmit={handleSubmit(onSubmit)} noValidate>
      {serverError && <Alert severity="error">{serverError}</Alert>}
      <TextField
        label="New password"
        type="password"
        autoComplete="new-password"
        fullWidth
        autoFocus
        error={Boolean(errors.password)}
        helperText={errors.password?.message}
        {...register('password', {
          required: 'Password is required',
          minLength: { value: MIN_LENGTH, message: `Use at least ${MIN_LENGTH} characters` },
        })}
      />
      <TextField
        label="Repeat new password"
        type="password"
        autoComplete="new-password"
        fullWidth
        error={Boolean(errors.confirm)}
        helperText={errors.confirm?.message}
        {...register('confirm', {
          validate: (value) => value === getValues('password') || 'Passwords do not match',
        })}
      />
      <Button
        type="submit"
        variant="contained"
        size="large"
        disabled={isSubmitting}
        startIcon={isSubmitting ? <CircularProgress size={18} color="inherit" /> : null}
      >
        {isSubmitting ? 'Saving…' : 'Set new password'}
      </Button>
    </Stack>
  );
}
