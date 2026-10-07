'use client';

import { useRef, useState } from 'react';
import Box from '@mui/material/Box';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';
import Button from '@mui/material/Button';
import CircularProgress from '@mui/material/CircularProgress';
import CloudUploadOutlinedIcon from '@mui/icons-material/CloudUploadOutlined';
import ScienceOutlinedIcon from '@mui/icons-material/ScienceOutlined';
import { ACCEPTED_EXTENSIONS } from '@/services/salesService';

/** Drag-and-drop / browse area for the sales workbook. */
export default function SalesUploadZone({ onFile, onSample, processing, compact = false }) {
  const input = useRef(null);
  const [dragging, setDragging] = useState(false);

  const handleFiles = (files) => {
    const file = files?.[0];
    if (file) onFile(file);
  };

  return (
    <Box
      onDragOver={(e) => {
        e.preventDefault();
        setDragging(true);
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={(e) => {
        e.preventDefault();
        setDragging(false);
        if (!processing) handleFiles(e.dataTransfer.files);
      }}
      sx={{
        border: 2,
        borderStyle: 'dashed',
        borderColor: dragging ? 'primary.main' : 'divider',
        bgcolor: dragging ? 'rgba(31,95,214,0.04)' : 'background.paper',
        borderRadius: 3,
        p: compact ? 2.5 : { xs: 3, md: 5 },
        textAlign: 'center',
        transition: 'all .15s',
      }}
    >
      <input
        ref={input}
        type="file"
        hidden
        accept={ACCEPTED_EXTENSIONS.join(',')}
        aria-label="Sales Excel file"
        onChange={(e) => {
          handleFiles(e.target.files);
          e.target.value = '';
        }}
      />
      {processing ? (
        <Stack spacing={1.5} sx={{ alignItems: 'center', py: compact ? 0 : 2 }} role="status">
          <CircularProgress size={32} />
          <Typography variant="subtitle1">Reading and converting your workbook…</Typography>
        </Stack>
      ) : (
        <Stack spacing={1.5} sx={{ alignItems: 'center' }}>
          {!compact && (
            <Box sx={{ width: 56, height: 56, borderRadius: '50%', display: 'grid', placeItems: 'center', bgcolor: 'rgba(31,95,214,0.08)', color: 'primary.main' }}>
              <CloudUploadOutlinedIcon />
            </Box>
          )}
          <Typography variant={compact ? 'subtitle2' : 'h6'}>
            {compact ? 'Upload a different workbook' : 'Drag & drop your sales workbook here'}
          </Typography>
          {!compact && (
            <Typography variant="body2" color="text.secondary" sx={{ maxWidth: 560 }}>
              Excel .xlsx, first sheet, max 10 MB. Expected columns: CustomerName, Country, Location, Month, Year, Product,
              Unit Of Measurement, Quantity, Amount, Currency. Required: CustomerName, Product, Amount and Month + Year (or Date).
            </Typography>
          )}
          <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1}>
            <Button variant="contained" startIcon={<CloudUploadOutlinedIcon />} onClick={() => input.current?.click()}>
              Browse files
            </Button>
            {onSample && (
              <Button variant="outlined" startIcon={<ScienceOutlinedIcon />} onClick={onSample}>
                Load sample file (demo data)
              </Button>
            )}
          </Stack>
        </Stack>
      )}
    </Box>
  );
}
