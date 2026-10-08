'use client';

import { useEffect, useRef, useState } from 'react';
import TextField from '@mui/material/TextField';
import InputAdornment from '@mui/material/InputAdornment';
import IconButton from '@mui/material/IconButton';
import SearchRoundedIcon from '@mui/icons-material/SearchRounded';
import CloseRoundedIcon from '@mui/icons-material/CloseRounded';
import useDebounce from '@/hooks/useDebounce';

/** Debounced search input. `value` is the committed search; `onSearch` fires 350 ms after typing stops. */
export default function DealerSearchField({ value, onSearch, placeholder = 'Search dealers by name, company, city or email...' }) {
  const [text, setText] = useState(value);
  const debounced = useDebounce(text, 350);
  const lastCommitted = useRef(value);

  // Commit debounced input.
  useEffect(() => {
    if (debounced.trim() !== lastCommitted.current) {
      lastCommitted.current = debounced.trim();
      onSearch(debounced.trim());
    }
  }, [debounced, onSearch]);

  // Follow external changes (e.g. "Clear filters").
  useEffect(() => {
    if (value !== lastCommitted.current) {
      lastCommitted.current = value;
      setText(value);
    }
  }, [value]);

  return (
    <TextField
      fullWidth
      size="small"
      value={text}
      onChange={(e) => setText(e.target.value)}
      placeholder={placeholder}
      sx={{ bgcolor: 'background.paper' }}
      slotProps={{
        htmlInput: { 'aria-label': 'Search dealers' },
        input: {
          startAdornment: (
            <InputAdornment position="start">
              <SearchRoundedIcon fontSize="small" />
            </InputAdornment>
          ),
          endAdornment: text ? (
            <InputAdornment position="end">
              <IconButton size="small" aria-label="Clear search" onClick={() => setText('')}>
                <CloseRoundedIcon fontSize="small" />
              </IconButton>
            </InputAdornment>
          ) : null,
        },
      }}
    />
  );
}
