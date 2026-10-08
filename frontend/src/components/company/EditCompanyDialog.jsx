'use client';

import { useEffect, useRef, useState } from 'react';
import { useForm } from 'react-hook-form';
import Dialog from '@mui/material/Dialog';
import DialogTitle from '@mui/material/DialogTitle';
import DialogContent from '@mui/material/DialogContent';
import DialogActions from '@mui/material/DialogActions';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Alert from '@mui/material/Alert';
import CircularProgress from '@mui/material/CircularProgress';
import CompanyFormFields, { EMPTY_COMPANY, companyToForm, formToPayload } from '@/components/admin/CompanyFormFields';
import companyService from '@/services/companyService';
import useAsync from '@/hooks/useAsync';

/** The signed-in user's own company profile (Company Administrators). onSaved receives the updated company. */
export default function EditCompanyDialog({ open, company, onClose, onSaved }) {
  const [serverError, setServerError] = useState('');
  const errorRef = useRef(null);
  const { data: options } = useAsync(() => (open ? companyService.getCompanyOptions() : Promise.resolve(null)), [open]);
  const {
    register,
    control,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting, isDirty },
  } = useForm({ defaultValues: EMPTY_COMPANY });

  // Start from the current details every time the dialog opens.
  useEffect(() => {
    if (open && company) {
      reset(companyToForm(company));
      setServerError('');
    }
  }, [open, company, reset]);

  useEffect(() => {
    if (serverError) errorRef.current?.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }, [serverError]);

  const close = () => {
    if (!isSubmitting) onClose();
  };

  const onSubmit = async (values) => {
    setServerError('');
    try {
      onSaved(await companyService.updateCompanyDetails(formToPayload(values)));
    } catch (error) {
      setServerError(error.message);
    }
  };

  return (
    <Dialog open={open} onClose={close} maxWidth="md" fullWidth>
      <DialogTitle>Edit company details</DialogTitle>
      <DialogContent dividers>
        <Box component="form" id="edit-company-form" onSubmit={handleSubmit(onSubmit)} noValidate>
          {serverError && (
            <Alert ref={errorRef} severity="error" sx={{ mb: 2 }}>
              {serverError}
            </Alert>
          )}
          <CompanyFormFields register={register} control={control} errors={errors} lookups={options} />
        </Box>
      </DialogContent>
      <DialogActions>
        <Button color="inherit" onClick={close} disabled={isSubmitting}>
          Cancel
        </Button>
        <Button
          type="submit"
          form="edit-company-form"
          variant="contained"
          disabled={isSubmitting || !isDirty}
          startIcon={isSubmitting ? <CircularProgress size={16} color="inherit" /> : null}
        >
          {isSubmitting ? 'Saving…' : 'Save changes'}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
