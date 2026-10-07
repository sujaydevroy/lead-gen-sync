'use client';

import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';
import Pagination from '@mui/material/Pagination';
import Select from '@mui/material/Select';
import MenuItem from '@mui/material/MenuItem';
import { PAGE_SIZE_OPTIONS } from '@/types/dealer';

/** "Showing 1–20 of 128 dealers" + page links + page-size selector. Works with server-side pagination. */
export default function DealerPagination({ page, pageSize, total, totalPages, onPageChange, onPageSizeChange }) {
  if (!total) return null;
  const from = (page - 1) * pageSize + 1;
  const to = Math.min(page * pageSize, total);

  return (
    <Stack
      direction={{ xs: 'column', md: 'row' }}
      spacing={1.5}
      sx={{ alignItems: 'center', justifyContent: 'space-between', px: { xs: 0, md: 2 }, py: 1.5 }}
    >
      <Typography variant="body2" color="text.secondary" aria-live="polite">
        Showing {from}–{to} of {total} dealers
      </Typography>
      <Pagination
        page={page}
        count={totalPages}
        onChange={(_, value) => onPageChange(value)}
        color="primary"
        shape="rounded"
        showFirstButton={totalPages > 5}
        showLastButton={totalPages > 5}
        siblingCount={1}
        size="medium"
      />
      <Stack direction="row" spacing={1} sx={{ alignItems: 'center' }}>
        <Typography variant="body2" color="text.secondary" id="page-size-label">
          Rows per page
        </Typography>
        <Select
          size="small"
          value={pageSize}
          onChange={(e) => onPageSizeChange(Number(e.target.value))}
          inputProps={{ 'aria-labelledby': 'page-size-label' }}
          SelectDisplayProps={{ 'aria-labelledby': 'page-size-label' }}
          sx={{ '& .MuiSelect-select': { py: 0.6 } }}
        >
          {PAGE_SIZE_OPTIONS.map((size) => (
            <MenuItem key={size} value={size}>
              {size}
            </MenuItem>
          ))}
        </Select>
      </Stack>
    </Stack>
  );
}
