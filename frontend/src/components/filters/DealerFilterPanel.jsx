'use client';

import { useEffect, useMemo, useState } from 'react';
import Box from '@mui/material/Box';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';
import Button from '@mui/material/Button';
import Divider from '@mui/material/Divider';
import Skeleton from '@mui/material/Skeleton';
import FilterListRoundedIcon from '@mui/icons-material/FilterListRounded';
import CountryLabel from '@/components/ui/CountryLabel';
import FilterGroup from './FilterGroup';

const sameFilters = (a, b) => JSON.stringify(a) === JSON.stringify(b);

/**
 * Left-hand dealer filters: Country, Region (depends on Country), Status, Dealer Type,
 * Sector and Sub-sector (scoped to the company's sector from sector.json).
 *
 * Edits are kept as a draft. With `instant` they are applied on every change;
 * otherwise "Apply Filters" commits them.
 */
export default function DealerFilterPanel({ facets, applied, onApply, onClearAll, instant = true, companySector, onDone }) {
  const [draft, setDraft] = useState(applied);

  useEffect(() => {
    setDraft(applied);
  }, [applied]);

  const dirty = !sameFilters(draft, applied);
  const activeCount = Object.values(draft).reduce((n, list) => n + list.length, 0);

  const regionOptions = useMemo(() => {
    if (!facets) return [];
    const counts = new Map(facets.regions.map((r) => [r.value, r.count]));
    const available = draft.countries.length
      ? [...new Set(draft.countries.flatMap((c) => facets.regionsByCountry[c] || []))]
      : [...new Set(Object.values(facets.regionsByCountry).flat())];
    const order = facets.regions.map((r) => r.value);
    available.sort((a, b) => (order.indexOf(a) === -1 ? 99 : order.indexOf(a)) - (order.indexOf(b) === -1 ? 99 : order.indexOf(b)));
    // Counts reflect the applied filters; when the draft differs they may be stale, so hide them.
    const showCounts = sameFilters(draft.countries, applied.countries);
    return available.map((value) => ({ value, count: showCounts ? counts.get(value) ?? 0 : null }));
  }, [facets, draft.countries, applied.countries]);

  const update = (next) => {
    // Drop selected regions that the chosen countries don't have.
    if (facets && next.countries.length) {
      const allowed = new Set(next.countries.flatMap((c) => facets.regionsByCountry[c] || []));
      next = { ...next, regions: next.regions.filter((r) => allowed.has(r)) };
    }
    setDraft(next);
    if (instant) onApply(next);
  };

  const toggle = (group) => (value) => {
    const list = draft[group];
    update({ ...draft, [group]: list.includes(value) ? list.filter((v) => v !== value) : [...list, value] });
  };

  const apply = () => {
    onApply(draft);
    onDone?.();
  };

  if (!facets) {
    return (
      <Stack spacing={1.5} sx={{ p: 2.5 }} aria-busy="true" aria-label="Loading filters">
        {Array.from({ length: 10 }).map((_, i) => (
          <Skeleton key={i} height={24} width={i % 4 === 0 ? '45%' : '85%'} />
        ))}
      </Stack>
    );
  }

  const sectorName = companySector?.sector;

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <Stack direction="row" sx={{ px: 2.5, py: 2, alignItems: 'center', justifyContent: 'space-between' }}>
        <Stack direction="row" spacing={1} sx={{ alignItems: 'center' }}>
          <FilterListRoundedIcon fontSize="small" color="primary" />
          <Typography variant="h6" component="h2">
            Filters
          </Typography>
        </Stack>
        <Button size="small" color="inherit" onClick={onClearAll} disabled={activeCount === 0 && !dirty}>
          Clear All
        </Button>
      </Stack>
      <Divider />

      <Stack spacing={2.25} divider={<Divider flexItem />} sx={{ px: 2.5, py: 2, overflowY: 'auto', flexGrow: 1 }}>
        <FilterGroup
          title="Country"
          options={facets.countries}
          selected={draft.countries}
          onToggle={toggle('countries')}
          renderLabel={(value) => <CountryLabel country={value} />}
          maxVisible={10}
        />
        <FilterGroup
          title="Region"
          hint={draft.countries.length ? `Regions in ${draft.countries.join(', ')}` : 'All regions · select a country to narrow'}
          options={regionOptions}
          selected={draft.regions}
          onToggle={toggle('regions')}
        />
        <FilterGroup title="Dealer Status" options={facets.statuses} selected={draft.statuses} onToggle={toggle('statuses')} />
        <FilterGroup title="Dealer Type" options={facets.types} selected={draft.types} onToggle={toggle('types')} />
        <FilterGroup
          title="Sector"
          hint="Your company's sector (Company Details)"
          options={facets.sectors}
          selected={draft.sectors}
          onToggle={toggle('sectors')}
          emptyText="No sector is configured for your company."
        />
        <FilterGroup
          title="Sub-sector"
          hint={sectorName ? `Sub-sectors of ${sectorName} · matched on dealer products` : undefined}
          options={facets.subSectors}
          selected={draft.subSectors}
          onToggle={toggle('subSectors')}
          maxVisible={8}
          searchable
          emptyText="No sub-sectors available for your company's sector."
        />
      </Stack>

      <Divider />
      <Stack direction="row" spacing={1} sx={{ p: 2 }}>
        <Button fullWidth variant="outlined" color="inherit" onClick={onClearAll} disabled={activeCount === 0 && !dirty}>
          Clear All
        </Button>
        <Button fullWidth variant="contained" onClick={apply} disabled={instant ? !onDone : !dirty}>
          {instant && onDone ? 'Show results' : 'Apply Filters'}
        </Button>
      </Stack>
      {instant && !onDone && (
        <Typography variant="caption" sx={{ px: 2, pb: 2, mt: -1 }}>
          Filters apply instantly. Turn this off in Settings to apply manually.
        </Typography>
      )}
    </Box>
  );
}
