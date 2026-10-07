'use client';

import Stack from '@mui/material/Stack';
import Chip from '@mui/material/Chip';
import Typography from '@mui/material/Typography';
import Button from '@mui/material/Button';

const GROUP_LABELS = {
  countries: 'Country',
  regions: 'Region',
  statuses: 'Status',
  types: 'Type',
  sectors: 'Sector',
  subSectors: 'Sub-sector',
};

/** Removable chips for every applied filter value: [India ×] [North ×] [Active ×] */
export default function ActiveFilterChips({ filters, search, onRemove, onClearSearch, onClearAll }) {
  const chips = Object.entries(filters).flatMap(([group, values]) => values.map((value) => ({ group, value })));
  if (!chips.length && !search) return null;

  return (
    <Stack direction="row" spacing={1} sx={{ alignItems: 'center', flexWrap: 'wrap', rowGap: 1 }} aria-label="Active filters">
      <Typography variant="body2" color="text.secondary" sx={{ fontWeight: 600, mr: 0.5 }}>
        Filters:
      </Typography>
      {search && <Chip size="small" label={`Search: "${search}"`} onDelete={onClearSearch} color="primary" variant="outlined" />}
      {chips.map(({ group, value }) => (
        <Chip
          key={`${group}-${value}`}
          size="small"
          label={value}
          title={`${GROUP_LABELS[group]}: ${value}`}
          onDelete={() => onRemove(group, value)}
          color="primary"
          variant="outlined"
          sx={{ bgcolor: 'rgba(31,95,214,0.06)' }}
        />
      ))}
      <Button size="small" onClick={onClearAll} sx={{ ml: 0.5 }}>
        Clear all
      </Button>
    </Stack>
  );
}
