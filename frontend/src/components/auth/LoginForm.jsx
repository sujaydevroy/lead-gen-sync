'use client';

import { useEffect, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useForm } from 'react-hook-form';
import Box from '@mui/material/Box';
import Stack from '@mui/material/Stack';
import TextField from '@mui/material/TextField';
import Button from '@mui/material/Button';
import Checkbox from '@mui/material/Checkbox';
import FormControlLabel from '@mui/material/FormControlLabel';
import IconButton from '@mui/material/IconButton';
import InputAdornment from '@mui/material/InputAdornment';
import Alert from '@mui/material/Alert';
import Link from '@mui/material/Link';
import Typography from '@mui/material/Typography';
import CircularProgress from '@mui/material/CircularProgress';
import Visibility from '@mui/icons-material/Visibility';
import VisibilityOff from '@mui/icons-material/VisibilityOff';
import MailOutlineRoundedIcon from '@mui/icons-material/MailOutlineRounded';
import LockOutlinedIcon from '@mui/icons-material/LockOutlined';
import { useAuth } from '@/components/providers/AuthProvider';
import ForgotPasswordDialog from './ForgotPasswordDialog';
import { homePathFor } from '@/lib/roles';
import { EMAIL_PATTERN, safeRedirect } from './validation';

export default function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { login, status, verified, user } = useAuth();
  const [showPassword, setShowPassword] = useState(false);
  const [forgotOpen, setForgotOpen] = useState(false);
  const [serverError, setServerError] = useState('');

  const {
    register,
    handleSubmit,
    getValues,
    setValue,
    formState: { errors, isSubmitting },
  } = useForm({ defaultValues: { email: '', password: '', remember: true } });

  // Already signed in (session confirmed by the API): skip the form.
  useEffect(() => {
    if (status === 'authenticated' && verified) router.replace(safeRedirect(searchParams.get('next'), homePathFor(user)));
  }, [status, verified, user, router, searchParams]);

  const onSubmit = async (values) => {
    setServerError('');
    try {
      const session = await login(values);
      router.replace(safeRedirect(searchParams.get('next'), homePathFor(session.user)));
    } catch (error) {
      setServerError(error.status === 401 ? 'Invalid email or password. Please try again.' : error.message);
    }
  };

  return (
    <Box component="form" onSubmit={handleSubmit(onSubmit)} noValidate>
      <Stack spacing={2.25}>
        {serverError && (
          <Alert severity="error" onClose={() => setServerError('')}>
            {serverError}
          </Alert>
        )}

        <TextField
          label="Company Email"
          type="email"
          autoComplete="username"
          fullWidth
          autoFocus
          error={Boolean(errors.email)}
          helperText={errors.email?.message}
          slotProps={{
            input: {
              startAdornment: (
                <InputAdornment position="start">
                  <MailOutlineRoundedIcon fontSize="small" />
                </InputAdornment>
              ),
            },
          }}
          {...register('email', {
            required: 'Company email is required',
            pattern: { value: EMAIL_PATTERN, message: 'Enter a valid email address' },
          })}
        />

        <TextField
          label="Password"
          type={showPassword ? 'text' : 'password'}
          autoComplete="current-password"
          fullWidth
          error={Boolean(errors.password)}
          helperText={errors.password?.message}
          slotProps={{
            input: {
              startAdornment: (
                <InputAdornment position="start">
                  <LockOutlinedIcon fontSize="small" />
                </InputAdornment>
              ),
              endAdornment: (
                <InputAdornment position="end">
                  <IconButton
                    aria-label={showPassword ? 'Hide password' : 'Show password'}
                    onClick={() => setShowPassword((v) => !v)}
                    edge="end"
                    size="small"
                  >
                    {showPassword ? <VisibilityOff fontSize="small" /> : <Visibility fontSize="small" />}
                  </IconButton>
                </InputAdornment>
              ),
            },
          }}
          {...register('password', {
            required: 'Password is required',
            minLength: { value: 6, message: 'Password must be at least 6 characters' },
          })}
        />

        <Stack direction="row" sx={{ alignItems: 'center', justifyContent: 'space-between' }}>
          <FormControlLabel
            control={<Checkbox defaultChecked {...register('remember')} />}
            label={<Typography variant="body2">Remember me</Typography>}
          />
          <Link component="button" type="button" variant="body2" underline="hover" onClick={() => setForgotOpen(true)}>
            Forgot password?
          </Link>
        </Stack>

        <Button
          type="submit"
          variant="contained"
          size="large"
          fullWidth
          disabled={isSubmitting}
          startIcon={isSubmitting ? <CircularProgress size={18} color="inherit" /> : null}
          sx={{ py: 1.25 }}
        >
          {isSubmitting ? 'Signing in…' : 'Login'}
        </Button>

        <Alert severity="info" variant="outlined" sx={{ '& .MuiAlert-message': { width: '100%' } }}>
          <Typography variant="body2" sx={{ fontWeight: 600 }}>
            Demo account
          </Typography>
          <Typography variant="body2">
            <Link
              component="button"
              type="button"
              onClick={() => setValue('email', 'john.smith@abc.com', { shouldValidate: true })}
            >
              john.smith@abc.com
            </Link>{' '}
            — use the password set with <code>python -m app.cli setup</code> (backend).
          </Typography>
        </Alert>
      </Stack>

      <ForgotPasswordDialog open={forgotOpen} onClose={() => setForgotOpen(false)} defaultEmail={forgotOpen ? getValues('email') : ''} />
    </Box>
  );
}
