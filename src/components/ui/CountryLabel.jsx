import Box from '@mui/material/Box';
import { countryFlag } from '@/lib/countries';

export default function CountryLabel({ country, sx }) {
  const flag = countryFlag(country);
  return (
    <Box component="span" sx={{ display: 'inline-flex', alignItems: 'center', gap: 0.75, ...sx }}>
      {flag && (
        <Box component="span" aria-hidden sx={{ fontSize: '1.05em', lineHeight: 1 }}>
          {flag}
        </Box>
      )}
      {country}
    </Box>
  );
}
