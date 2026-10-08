'use client';

import { useMemo, useState } from 'react';
import Box from '@mui/material/Box';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';
import Checkbox from '@mui/material/Checkbox';
import FormControlLabel from '@mui/material/FormControlLabel';
import Button from '@mui/material/Button';
import TextField from '@mui/material/TextField';
import InputAdornment from '@mui/material/InputAdornment';
import SearchRoundedIcon from '@mui/icons-material/SearchRounded';

/**
 * A titled group of checkbox options with counts, e.g. "☐ India (12)".
 * @param {{ title: string, hint?: React.ReactNode, options: { value: string, count?: number|null }[],
 *           selected: string[], onToggle: (value: string) => void, renderLabel?: (value: string) => React.ReactNode,
 *           maxVisible?: number, searchable?: boolean, emptyText?: string }} props
 */
export default function FilterGroup({
  title,
  hint,
  options,
  selected,
  onToggle,
  renderLabel,
  maxVisible = 8,
  searchable = false,
  emptyText = 'No options available',
}) {
  const [expanded, setExpanded] = useState(false);
  const [query, setQuery] = useState('');
  const id = `filter-${title.toLowerCase().replace(/\W+/g, '-')}`;

  const visibleOptions = useMemo(() => {
    const term = query.trim().toLowerCase();
    const matched = term ? options.filter((o) => o.value.toLowerCase().includes(term)) : options;
    // Keep selected options visible even when the list is collapsed.
    if (expanded || term || matched.length <= maxVisible) return matched;
    const head = matched.slice(0, maxVisible);
    const extraSelected = matched.slice(maxVisible).filter((o) => selected.includes(o.value));
    return [...head, ...extraSelected];
  }, [options, query, expanded, maxVisible, selected]);

  const hiddenCount = options.length - visibleOptions.length;

  return (
    <Box component="fieldset" sx={{ border: 0, p: 0, m: 0, minWidth: 0 }} aria-labelledby={id}>
      <Stack direction="row" sx={{ alignItems: 'baseline', justifyContent: 'space-between', mb: 0.5 }}>
        <Typography id={id} variant="overline" component="legend" sx={{ lineHeight: 2 }}>
          {title}
        </Typography>
        {selected.length > 0 && (
          <Typography variant="caption" color="primary" sx={{ fontWeight: 600 }}>
            {selected.length} selected
          </Typography>
        )}
      </Stack>
      {hint && (
        <Typography variant="caption" component="div" sx={{ mb: 0.75, mt: -0.25 }}>
          {hint}
        </Typography>
      )}
      {searchable && options.length > maxVisible && (
        <TextField
          size="small"
          fullWidth
          placeholder={`Search ${title.toLowerCase()}…`}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          sx={{ mb: 0.75, '& .MuiInputBase-input': { py: 0.75, fontSize: '0.85rem' } }}
          slotProps={{
            input: {
              startAdornment: (
                <InputAdornment position="start">
                  <SearchRoundedIcon sx={{ fontSize: 18 }} />
                </InputAdornment>
              ),
            },
            htmlInput: { 'aria-label': `Search ${title}` },
          }}
        />
      )}
      {options.length === 0 && (
        <Typography variant="body2" color="text.secondary" sx={{ py: 0.5 }}>
          {emptyText}
        </Typography>
      )}
      <Stack>
        {visibleOptions.map(({ value, count }) => {
          const checked = selected.includes(value);
          const disabled = !checked && count === 0;
          return (
            <FormControlLabel
              key={value}
              disabled={disabled}
              sx={{ mx: 0, mr: 0, '& .MuiFormControlLabel-label': { flexGrow: 1, minWidth: 0 } }}
              control={<Checkbox checked={checked} onChange={() => onToggle(value)} sx={{ p: 0.6, mr: 0.75 }} />}
              label={
                <Stack direction="row" spacing={1} sx={{ alignItems: 'center', justifyContent: 'space-between' }}>
                  <Typography variant="body2" sx={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {renderLabel ? renderLabel(value) : value}
                  </Typography>
                  {count !== undefined && count !== null && (
                    <Typography variant="caption" sx={{ fontVariantNumeric: 'tabular-nums', flexShrink: 0 }}>
                      ({count})
                    </Typography>
                  )}
                </Stack>
              }
            />
          );
        })}
      </Stack>
      {!query && options.length > maxVisible && (
        <Button size="small" onClick={() => setExpanded((v) => !v)} sx={{ mt: 0.25, px: 0.5, minWidth: 0 }}>
          {expanded ? 'Show less' : `Show all (${hiddenCount} more)`}
        </Button>
      )}
    </Box>
  );
}
