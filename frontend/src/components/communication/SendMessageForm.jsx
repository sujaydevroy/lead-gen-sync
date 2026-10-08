'use client';

import { useRef } from 'react';
import { useForm, Controller } from 'react-hook-form';
import Stack from '@mui/material/Stack';
import TextField from '@mui/material/TextField';
import Button from '@mui/material/Button';
import Chip from '@mui/material/Chip';
import Typography from '@mui/material/Typography';
import FormHelperText from '@mui/material/FormHelperText';
import CircularProgress from '@mui/material/CircularProgress';
import AttachFileRoundedIcon from '@mui/icons-material/AttachFileRounded';
import SendRoundedIcon from '@mui/icons-material/SendRounded';
import { useAuth } from '@/components/providers/AuthProvider';
import { useNotify } from '@/components/providers/NotificationProvider';
import communicationService from '@/services/communicationService';
import { MAX_ATTACHMENT_BYTES } from '@/types/communication';
import { formatFileSize } from '@/lib/format';

const ACCEPT = '.pdf,.doc,.docx,.xls,.xlsx,.csv,.png,.jpg,.jpeg,.txt';

/** Send Message form: To / Subject / Message / Attachment with validation. */
export default function SendMessageForm({ dealer, onCancel, onSent }) {
  const { user } = useAuth();
  const notify = useNotify();
  const fileInput = useRef(null);
  const {
    register,
    control,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm({ defaultValues: { subject: '', message: '', attachment: null } });

  const onSubmit = async (values) => {
    try {
      const saved = await communicationService.sendMessage({
        dealerId: dealer.dealer_id,
        subject: values.subject,
        message: values.message,
        attachment: values.attachment,
        sender: user?.name,
      });
      notify(`Message sent to ${dealer.dealer_name}`, 'success');
      reset();
      if (fileInput.current) fileInput.current.value = '';
      onSent?.(saved);
    } catch (error) {
      notify(error.message || 'The message could not be sent. Please try again.', 'error');
    }
  };

  const to = `${dealer.dealer_name} <${dealer.email}>`;

  return (
    <Stack component="form" spacing={2} onSubmit={handleSubmit(onSubmit)} noValidate aria-label={`Send message to ${dealer.dealer_name}`}>
      <TextField label="To" value={to} size="small" fullWidth slotProps={{ input: { readOnly: true } }} />
      <TextField
        label="Subject"
        size="small"
        fullWidth
        required
        error={Boolean(errors.subject)}
        helperText={errors.subject?.message}
        {...register('subject', {
          required: 'Subject is required',
          validate: (v) => v.trim().length >= 3 || 'Subject must be at least 3 characters',
          maxLength: { value: 150, message: 'Subject must be 150 characters or fewer' },
        })}
      />
      <TextField
        label="Message"
        fullWidth
        required
        multiline
        minRows={5}
        maxRows={12}
        error={Boolean(errors.message)}
        helperText={errors.message?.message || 'At least 10 characters'}
        {...register('message', {
          required: 'Message is required',
          validate: (v) => v.trim().length >= 10 || 'Message must be at least 10 characters',
          maxLength: { value: 5000, message: 'Message must be 5,000 characters or fewer' },
        })}
      />

      <Controller
        name="attachment"
        control={control}
        rules={{
          validate: (file) => !file || file.size <= MAX_ATTACHMENT_BYTES || 'Attachment must be 10 MB or smaller',
        }}
        render={({ field, fieldState }) => (
          <div>
            <input
              ref={fileInput}
              type="file"
              hidden
              accept={ACCEPT}
              aria-label="Attachment file"
              onChange={(e) => field.onChange(e.target.files?.[0] || null)}
            />
            <Stack direction="row" spacing={1.5} sx={{ alignItems: 'center', flexWrap: 'wrap', rowGap: 1 }}>
              <Button variant="outlined" size="small" startIcon={<AttachFileRoundedIcon />} onClick={() => fileInput.current?.click()}>
                Upload File
              </Button>
              {field.value ? (
                <Chip
                  label={`${field.value.name} (${formatFileSize(field.value.size)})`}
                  onDelete={() => {
                    field.onChange(null);
                    if (fileInput.current) fileInput.current.value = '';
                  }}
                  sx={{ maxWidth: '100%' }}
                />
              ) : (
                <Typography variant="caption">Optional · PDF, Office, image or text · max 10 MB</Typography>
              )}
            </Stack>
            {fieldState.error && <FormHelperText error>{fieldState.error.message}</FormHelperText>}
          </div>
        )}
      />

      <Stack direction="row" spacing={1} sx={{ justifyContent: 'flex-end' }}>
        <Button
          color="inherit"
          onClick={() => {
            reset();
            if (fileInput.current) fileInput.current.value = '';
            onCancel?.();
          }}
          disabled={isSubmitting}
        >
          Cancel
        </Button>
        <Button
          type="submit"
          variant="contained"
          disabled={isSubmitting}
          startIcon={isSubmitting ? <CircularProgress size={16} color="inherit" /> : <SendRoundedIcon />}
        >
          {isSubmitting ? 'Sending…' : 'Send Message'}
        </Button>
      </Stack>
    </Stack>
  );
}
