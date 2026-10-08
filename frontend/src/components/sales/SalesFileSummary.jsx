'use client';

import { useState } from 'react';
import Stack from '@mui/material/Stack';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Button from '@mui/material/Button';
import Chip from '@mui/material/Chip';
import Collapse from '@mui/material/Collapse';
import Alert from '@mui/material/Alert';
import DescriptionOutlinedIcon from '@mui/icons-material/DescriptionOutlined';
import CloseRoundedIcon from '@mui/icons-material/CloseRounded';
import { formatDate, formatFileSize, formatNumber } from '@/lib/format';

export default function SalesFileSummary({ metadata, onClear }) {
  const [showWarnings, setShowWarnings] = useState(false);
  return (
    <Box>
      <Stack direction={{ xs: 'column', md: 'row' }} spacing={2} sx={{ alignItems: { md: 'center' }, justifyContent: 'space-between' }}>
        <Stack direction="row" spacing={1.5} sx={{ alignItems: 'center', minWidth: 0 }}>
          <Box sx={{ width: 44, height: 44, borderRadius: 2, display: 'grid', placeItems: 'center', bgcolor: 'rgba(30,142,90,0.1)', color: 'success.main', flexShrink: 0 }}>
            <DescriptionOutlinedIcon />
          </Box>
          <Box sx={{ minWidth: 0 }}>
            <Typography variant="subtitle1" sx={{ wordBreak: 'break-all' }}>
              {metadata.name}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              {formatFileSize(metadata.size)} · uploaded {formatDate(metadata.uploadedAt, { withTime: true })}
            </Typography>
          </Box>
        </Stack>
        <Stack direction="row" spacing={1} sx={{ flexWrap: 'wrap', rowGap: 1, alignItems: 'center' }}>
          <Chip size="small" label={`${formatNumber(metadata.totalRows)} rows`} />
          <Chip size="small" color="success" variant="outlined" label={`${formatNumber(metadata.validRows)} converted`} />
          {metadata.skippedRows > 0 && <Chip size="small" color="warning" variant="outlined" label={`${metadata.skippedRows} skipped`} />}
          <Button size="small" color="inherit" startIcon={<CloseRoundedIcon />} onClick={onClear}>
            Close
          </Button>
        </Stack>
      </Stack>
      {metadata.warningCount > 0 && (
        <Alert
          severity="warning"
          sx={{ mt: 2 }}
          action={
            <Button color="inherit" size="small" onClick={() => setShowWarnings((v) => !v)}>
              {showWarnings ? 'Hide' : 'Details'}
            </Button>
          }
        >
          {metadata.warningCount} row{metadata.warningCount === 1 ? '' : 's'} had problems (missing amounts, dates or currency).
          <Collapse in={showWarnings}>
            <Box component="ul" sx={{ m: 0, mt: 1, pl: 2.5 }}>
              {metadata.warnings.map((w) => (
                <li key={`${w.row}-${w.message}`}>
                  Row {w.row}: {w.message}
                </li>
              ))}
            </Box>
          </Collapse>
        </Alert>
      )}
    </Box>
  );
}
