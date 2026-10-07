'use client';

import { useMemo } from 'react';
import Box from '@mui/material/Box';
import Stack from '@mui/material/Stack';
import Button from '@mui/material/Button';
import Typography from '@mui/material/Typography';
import DownloadRoundedIcon from '@mui/icons-material/DownloadRounded';
import ContentCopyRoundedIcon from '@mui/icons-material/ContentCopyRounded';
import useCopyToClipboard from '@/hooks/useCopyToClipboard';

const PREVIEW_LIMIT = 50;

/** JSON produced from the Excel sheet, with download / copy. */
export default function SalesJsonView({ records, fileName }) {
  const copy = useCopyToClipboard();
  const json = useMemo(() => JSON.stringify(records, null, 2), [records]);
  const preview = useMemo(
    () => (records.length > PREVIEW_LIMIT ? JSON.stringify(records.slice(0, PREVIEW_LIMIT), null, 2) : json),
    [records, json],
  );

  const download = () => {
    const blob = new Blob([json], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${(fileName || 'sales').replace(/\.xlsx.*$/i, '').replace(/[^\w-]+/g, '_')}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <Box sx={{ p: 2 }}>
      <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1} sx={{ mb: 1.5, justifyContent: 'space-between', alignItems: { sm: 'center' } }}>
        <Typography variant="body2" color="text.secondary">
          {records.length} records converted from Excel to JSON
          {records.length > PREVIEW_LIMIT ? ` · showing the first ${PREVIEW_LIMIT}` : ''}
        </Typography>
        <Stack direction="row" spacing={1}>
          <Button size="small" startIcon={<ContentCopyRoundedIcon />} onClick={() => copy(json, 'JSON')}>
            Copy JSON
          </Button>
          <Button size="small" variant="outlined" startIcon={<DownloadRoundedIcon />} onClick={download}>
            Download JSON
          </Button>
        </Stack>
      </Stack>
      <Box
        component="pre"
        sx={{
          m: 0,
          p: 2,
          bgcolor: '#0f1e3c',
          color: '#dbe6ff',
          borderRadius: 2,
          fontSize: 12.5,
          lineHeight: 1.55,
          maxHeight: 520,
          overflow: 'auto',
          fontFamily: 'ui-monospace, SFMono-Regular, Consolas, monospace',
        }}
        tabIndex={0}
        aria-label="Converted JSON"
      >
        {preview}
      </Box>
    </Box>
  );
}
