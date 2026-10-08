'use client';

import { useEffect, useRef, useState } from 'react';
import { useForm } from 'react-hook-form';
import Dialog from '@mui/material/Dialog';
import DialogTitle from '@mui/material/DialogTitle';
import DialogContent from '@mui/material/DialogContent';
import DialogActions from '@mui/material/DialogActions';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Grid from '@mui/material/Grid';
import TextField from '@mui/material/TextField';
import Typography from '@mui/material/Typography';
import Alert from '@mui/material/Alert';
import CircularProgress from '@mui/material/CircularProgress';
import { EMAIL_PATTERN } from '@/components/auth/validation';
import adminService from '@/services/adminService';
import CompanyFormFields, { EMPTY_COMPANY, formToPayload } from './CompanyFormFields';

const EMPTY_ADMIN = { adminName: '', adminEmail: '', adminJobTitle: '', adminPassword: '' };

/** New company + its first Company Administrator (who then adds the company's other users). */
export default function CreateCompanyDialog({ open, onClose, onCreated, lookups }) {
  const [serverError, setServerError] = useState('');
  const errorRef = useRef(null);
  const {
    register,
    control,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm({ defaultValues: { ...EMPTY_COMPANY, ...EMPTY_ADMIN } });

  // The error is shown above the fields: bring it into view when it appears.
  useEffect(() => {
    if (serverError) errorRef.current?.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }, [serverError]);

  const close = () => {
    if (isSubmitting) return;
    reset();
    setServerError('');
    onClose();
  };

  const onSubmit = async (values) => {
    setServerError('');
    try {
      const company = await adminService.createCompany({
        ...formToPayload(values),
        admin: {
          name: values.adminName.trim(),
          email: values.adminEmail.trim(),
          jobTitle: values.adminJobTitle.trim() || null,
          password: values.adminPassword,
        },
      });
      reset();
      onCreated(company);
    } catch (error) {
      setServerError(error.message);
    }
  };

  const adminField = (name, label, rules, props = {}) => (
    <TextField fullWidth label={label} error={Boolean(errors[name])} helperText={errors[name]?.message} {...register(name, rules)} {...props} />
  );

  return (
    <Dialog open={open} onClose={close} maxWidth="md" fullWidth>
      <DialogTitle>New company</DialogTitle>
      <DialogContent dividers>
        <Box component="form" id="create-company-form" onSubmit={handleSubmit(onSubmit)} noValidate>
          {serverError && (
            <Alert ref={errorRef} severity="error" sx={{ mb: 2 }}>
              {serverError}
            </Alert>
          )}
          <CompanyFormFields register={register} control={control} errors={errors} lookups={lookups} />

          <Typography variant="overline" color="text.secondary" component="p" sx={{ mt: 3 }}>
            Company administrator
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            The first user of the company. They sign in with this temporary password, change it under My Profile, and add
            the company&apos;s other users.
          </Typography>
          <Grid container spacing={2}>
            <Grid size={{ xs: 12, md: 6 }}>
              {adminField('adminName', 'Full name *', {
                required: 'Name is required',
                validate: (v) => v.trim().length >= 2 || 'Use at least 2 characters',
              })}
            </Grid>
            <Grid size={{ xs: 12, md: 6 }}>
              {adminField(
                'adminEmail',
                'Email *',
                { required: 'Email is required', pattern: { value: EMAIL_PATTERN, message: 'Enter a valid email address' } },
                { type: 'email' },
              )}
            </Grid>
            <Grid size={{ xs: 12, md: 6 }}>
              {adminField('adminJobTitle', 'Job title', { maxLength: { value: 80, message: 'Use 80 characters or fewer' } })}
            </Grid>
            <Grid size={{ xs: 12, md: 6 }}>
              {adminField(
                'adminPassword',
                'Temporary password *',
                { required: 'Password is required', minLength: { value: 8, message: 'Use at least 8 characters' } },
                { type: 'password', autoComplete: 'new-password' },
              )}
            </Grid>
          </Grid>
        </Box>
      </DialogContent>
      <DialogActions>
        <Button color="inherit" onClick={close} disabled={isSubmitting}>
          Cancel
        </Button>
        <Button
          type="submit"
          form="create-company-form"
          variant="contained"
          disabled={isSubmitting}
          startIcon={isSubmitting ? <CircularProgress size={16} color="inherit" /> : null}
        >
          {isSubmitting ? 'Creating…' : 'Create company'}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
