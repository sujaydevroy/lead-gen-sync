'use client';

import { useForm } from 'react-hook-form';
import Grid from '@mui/material/Grid';
import Stack from '@mui/material/Stack';
import Card from '@mui/material/Card';
import Box from '@mui/material/Box';
import Avatar from '@mui/material/Avatar';
import Typography from '@mui/material/Typography';
import TextField from '@mui/material/TextField';
import Button from '@mui/material/Button';
import Chip from '@mui/material/Chip';
import CircularProgress from '@mui/material/CircularProgress';
import PageHeader from '@/components/ui/PageHeader';
import SectionCard from '@/components/ui/SectionCard';
import InfoGrid from '@/components/ui/InfoGrid';
import { useAuth } from '@/components/providers/AuthProvider';
import { useNotify } from '@/components/providers/NotificationProvider';
import ChangePasswordCard from '@/components/users/ChangePasswordCard';
import authService from '@/services/authService';
import { initials } from '@/lib/format';

export default function ProfilePage() {
  const { user, company, updateUser } = useAuth();
  const notify = useNotify();
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting, isDirty },
  } = useForm({ values: { name: user.name, jobTitle: user.jobTitle, phone: user.phone } });

  const onSubmit = async (values) => {
    const trimmed = { name: values.name.trim(), jobTitle: values.jobTitle.trim(), phone: values.phone.trim() };
    const updated = await authService.updateProfile(user, trimmed);
    updateUser(updated);
    reset(trimmed);
    notify('Profile updated', 'success');
  };

  return (
    <>
      <PageHeader title="My Profile" subtitle="Your personal details in the portal" />

      <Card sx={{ mb: 3 }}>
        <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2.5} sx={{ p: 3, alignItems: { sm: 'center' } }}>
          <Avatar sx={{ width: 72, height: 72, bgcolor: 'secondary.main', fontSize: 26, fontWeight: 700 }}>{initials(user.name)}</Avatar>
          <Box>
            <Typography variant="h5" component="h2">
              {user.name}
            </Typography>
            <Typography color="text.secondary">
              {[user.jobTitle, company?.name].filter(Boolean).join(' · ')}
            </Typography>
            <Stack direction="row" spacing={1} sx={{ mt: 1.25, flexWrap: 'wrap', rowGap: 1 }}>
              <Chip size="small" color="primary" label={user.role} />
              {user.country && <Chip size="small" variant="outlined" label={[user.country, user.region].filter(Boolean).join(' · ')} />}
            </Stack>
          </Box>
        </Stack>
      </Card>

      <Grid container spacing={3}>
        <Grid size={{ xs: 12, lg: 7 }}>
          <SectionCard title="Edit profile" subtitle="Saved to your account">
            <Stack component="form" spacing={2.25} onSubmit={handleSubmit(onSubmit)} noValidate>
              <TextField
                label="Full name"
                fullWidth
                error={Boolean(errors.name)}
                helperText={errors.name?.message}
                {...register('name', {
                  required: 'Name is required',
                  validate: (v) => v.trim().length >= 2 || 'Name must be at least 2 characters',
                })}
              />
              <TextField
                label="Job title"
                fullWidth
                error={Boolean(errors.jobTitle)}
                helperText={errors.jobTitle?.message}
                {...register('jobTitle', { maxLength: { value: 80, message: 'Job title must be 80 characters or fewer' } })}
              />
              <TextField
                label="Phone"
                fullWidth
                error={Boolean(errors.phone)}
                helperText={errors.phone?.message}
                {...register('phone', {
                  pattern: { value: /^[+()\d\s-]{7,20}$/, message: 'Enter a valid phone number' },
                })}
              />
              <TextField label="Email" fullWidth value={user.email} disabled helperText="Managed by your company administrator" />
              <Stack direction="row" spacing={1} sx={{ justifyContent: 'flex-end' }}>
                <Button color="inherit" disabled={!isDirty || isSubmitting} onClick={() => reset()}>
                  Discard
                </Button>
                <Button
                  type="submit"
                  variant="contained"
                  disabled={!isDirty || isSubmitting}
                  startIcon={isSubmitting ? <CircularProgress size={16} color="inherit" /> : null}
                >
                  {isSubmitting ? 'Saving…' : 'Save changes'}
                </Button>
              </Stack>
            </Stack>
          </SectionCard>
        </Grid>
        <Grid size={{ xs: 12, lg: 5 }}>
          <SectionCard title="Account" sx={{ height: 'auto' }}>
            <InfoGrid
              columns={1}
              items={[
                { label: 'User ID', value: user.id },
                { label: 'Email', value: user.email },
                { label: 'Role', value: user.role },
                { label: 'Company', value: company ? `${company.name} (${company.id})` : '' },
                { label: 'Country', value: user.country },
                { label: 'Region', value: user.region },
              ]}
            />
          </SectionCard>
          <Box sx={{ mt: 3 }}>
            <ChangePasswordCard />
          </Box>
        </Grid>
      </Grid>
    </>
  );
}
