'use client';

import { useState } from 'react';
import { useForm } from 'react-hook-form';
import Dialog from '@mui/material/Dialog';
import DialogTitle from '@mui/material/DialogTitle';
import DialogContent from '@mui/material/DialogContent';
import DialogActions from '@mui/material/DialogActions';
import TextField from '@mui/material/TextField';
import Button from '@mui/material/Button';
import Alert from '@mui/material/Alert';
import Typography from '@mui/material/Typography';
import authService from '@/services/authService';
import { EMAIL_PATTERN } from './validation';

export default function ForgotPasswordDialog({ open, onClose, defaultEmail = '' }) {
  const [sentTo, setSentTo] = useState('');
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm({ values: { email: defaultEmail } });

  const close = () => {
    setSentTo('');
    reset();
    onClose();
  };

  const onSubmit = async ({ email }) => {
    await authService.requestPasswordReset(email);
    setSentTo(email);
  };

  return (
    <Dialog open={open} onClose={close} fullWidth maxWidth="xs">
      <form onSubmit={handleSubmit(onSubmit)} noValidate>
        <DialogTitle>Reset your password</DialogTitle>
        <DialogContent>
          {sentTo ? (
            <Alert severity="success">
              If an account exists for <strong>{sentTo}</strong>, a password reset link has been sent. While no email
              provider is configured on the server, the link is written to the API log instead.
            </Alert>
          ) : (
            <>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                Enter your company email and we&apos;ll send you a link to reset your password.
              </Typography>
              <TextField
                autoFocus
                fullWidth
                label="Company Email"
                type="email"
                autoComplete="email"
                error={Boolean(errors.email)}
                helperText={errors.email?.message}
                {...register('email', {
                  required: 'Company email is required',
                  pattern: { value: EMAIL_PATTERN, message: 'Enter a valid email address' },
                })}
              />
            </>
          )}
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2 }}>
          <Button onClick={close}>{sentTo ? 'Close' : 'Cancel'}</Button>
          {!sentTo && (
            <Button type="submit" variant="contained" disabled={isSubmitting}>
              {isSubmitting ? 'Sending…' : 'Send reset link'}
            </Button>
          )}
        </DialogActions>
      </form>
    </Dialog>
  );
}
