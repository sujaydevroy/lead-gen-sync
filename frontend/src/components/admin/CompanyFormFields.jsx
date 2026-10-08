'use client';

import { Controller } from 'react-hook-form';
import Grid from '@mui/material/Grid';
import TextField from '@mui/material/TextField';
import MenuItem from '@mui/material/MenuItem';
import Typography from '@mui/material/Typography';
import { EMAIL_PATTERN } from '@/components/auth/validation';

const PHONE_PATTERN = /^[+()\d\s-]{7,20}$/;
const NONE = '';

export const EMPTY_COMPANY = {
  name: '',
  logoText: '',
  industry: '',
  sector: '',
  website: '',
  email: '',
  phone: '',
  addressLine1: '',
  city: '',
  state: '',
  postalCode: '',
  country: '',
  region: '',
  registrationNumber: '',
  taxId: '',
  employees: '',
  founded: '',
};

/** Company from the API (address nested) -> flat form values. */
export function companyToForm(company) {
  const address = company.address || {};
  return {
    name: company.name || '',
    logoText: company.logoText || '',
    industry: company.industry || '',
    sector: company.sector || '',
    website: company.website || '',
    email: company.email || '',
    phone: company.phone || '',
    addressLine1: address.line1 || '',
    city: address.city || '',
    state: address.state || '',
    postalCode: address.postalCode || '',
    country: address.country || '',
    region: address.region || '',
    registrationNumber: company.registrationNumber || '',
    taxId: company.taxId || '',
    employees: company.employees ?? '',
    founded: company.founded ?? '',
  };
}

/** Form values -> API payload (empty text = not set, numbers as numbers). */
export function formToPayload(values) {
  const payload = {};
  Object.keys(EMPTY_COMPANY).forEach((key) => {
    const raw = typeof values[key] === 'string' ? values[key].trim() : values[key];
    payload[key] = raw === '' || raw === undefined ? null : raw;
  });
  ['employees', 'founded'].forEach((key) => {
    if (payload[key] !== null) payload[key] = Number(payload[key]);
  });
  return payload;
}

function SelectField({ control, name, label, options, helperText }) {
  return (
    <Controller
      name={name}
      control={control}
      render={({ field }) => (
        <TextField select fullWidth label={label} {...field} value={field.value ?? NONE} helperText={helperText}>
          <MenuItem value={NONE}>
            <em>Not set</em>
          </MenuItem>
          {options.map((option) => (
            <MenuItem key={option} value={option}>
              {option}
            </MenuItem>
          ))}
        </TextField>
      )}
    />
  );
}

/** The editable company profile, shared by "New company" and the company details page. */
export default function CompanyFormFields({ register, control, errors, lookups }) {
  const text = (name, label, rules = {}, props = {}) => (
    <TextField
      fullWidth
      label={label}
      error={Boolean(errors[name])}
      helperText={errors[name]?.message}
      {...register(name, rules)}
      {...props}
    />
  );
  const max = (n) => ({ maxLength: { value: n, message: `Use ${n} characters or fewer` } });
  const section = (title) => (
    <Grid size={12}>
      <Typography variant="overline" color="text.secondary">
        {title}
      </Typography>
    </Grid>
  );

  return (
    <Grid container spacing={2}>
      {section('Company')}
      <Grid size={{ xs: 12, md: 8 }}>
        {text('name', 'Company name *', {
          required: 'Company name is required',
          validate: (v) => v.trim().length >= 2 || 'Use at least 2 characters',
          ...max(200),
        })}
      </Grid>
      <Grid size={{ xs: 12, md: 4 }}>
        {text('logoText', 'Logo initials', max(10), { placeholder: 'From the name if empty' })}
      </Grid>
      <Grid size={{ xs: 12, md: 6 }}>{text('industry', 'Industry', max(150))}</Grid>
      <Grid size={{ xs: 12, md: 6 }}>
        <SelectField
          control={control}
          name="sector"
          label="Sector"
          options={lookups?.sectors || []}
          helperText="Scopes the company's Sector / Sub-sector dealer filters"
        />
      </Grid>

      {section('Contact')}
      <Grid size={{ xs: 12, md: 4 }}>
        {text('email', 'Email', { pattern: { value: EMAIL_PATTERN, message: 'Enter a valid email address' } }, { type: 'email' })}
      </Grid>
      <Grid size={{ xs: 12, md: 4 }}>
        {text('phone', 'Phone', { pattern: { value: PHONE_PATTERN, message: 'Enter a valid phone number' } })}
      </Grid>
      <Grid size={{ xs: 12, md: 4 }}>{text('website', 'Website', max(300))}</Grid>

      {section('Address')}
      <Grid size={12}>{text('addressLine1', 'Address', max(300))}</Grid>
      <Grid size={{ xs: 12, sm: 6, md: 4 }}>{text('city', 'City', max(100))}</Grid>
      <Grid size={{ xs: 12, sm: 6, md: 4 }}>{text('state', 'State / province', max(100))}</Grid>
      <Grid size={{ xs: 12, sm: 6, md: 4 }}>{text('postalCode', 'Postal code', max(20))}</Grid>
      <Grid size={{ xs: 12, sm: 6, md: 6 }}>
        <SelectField control={control} name="country" label="Country" options={lookups?.countries || []} />
      </Grid>
      <Grid size={{ xs: 12, sm: 6, md: 6 }}>
        <SelectField control={control} name="region" label="Region" options={lookups?.regions || []} />
      </Grid>

      {section('Registration')}
      <Grid size={{ xs: 12, sm: 6, md: 3 }}>{text('registrationNumber', 'Registration number', max(100))}</Grid>
      <Grid size={{ xs: 12, sm: 6, md: 3 }}>{text('taxId', 'Tax ID', max(100))}</Grid>
      <Grid size={{ xs: 12, sm: 6, md: 3 }}>
        {text('employees', 'Employees', { min: { value: 0, message: 'Must be 0 or more' } }, { type: 'number' })}
      </Grid>
      <Grid size={{ xs: 12, sm: 6, md: 3 }}>
        {text(
          'founded',
          'Founded (year)',
          {
            validate: (v) => v === '' || (Number(v) >= 1800 && Number(v) <= 2200) || 'Enter a year between 1800 and 2200',
          },
          { type: 'number' },
        )}
      </Grid>
    </Grid>
  );
}
