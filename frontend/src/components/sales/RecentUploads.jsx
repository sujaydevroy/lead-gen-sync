'use client';

import { useState } from 'react';
import Box from '@mui/material/Box';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';
import Button from '@mui/material/Button';
import Chip from '@mui/material/Chip';
import IconButton from '@mui/material/IconButton';
import Tooltip from '@mui/material/Tooltip';
import Skeleton from '@mui/material/Skeleton';
import Dialog from '@mui/material/Dialog';
import DialogTitle from '@mui/material/DialogTitle';
import DialogContent from '@mui/material/DialogContent';
import DialogContentText from '@mui/material/DialogContentText';
import DialogActions from '@mui/material/DialogActions';
import DeleteOutlineRoundedIcon from '@mui/icons-material/DeleteOutlineRounded';
import DownloadRoundedIcon from '@mui/icons-material/DownloadRounded';
import DescriptionOutlinedIcon from '@mui/icons-material/DescriptionOutlined';
import SectionCard from '@/components/ui/SectionCard';
import { useNotify } from '@/components/providers/NotificationProvider';
import salesService from '@/services/salesService';
import { formatDate, formatFileSize, formatNumber } from '@/lib/format';

/** Workbooks previously uploaded by the company (stored by the API). */
export default function RecentUploads({ uploads, loading, error, onReload, currentUploadId, onOpen, onDeleted, opening }) {
  const notify = useNotify();
  const [toDelete, setToDelete] = useState(null);
  const [deleting, setDeleting] = useState(false);

  if (!loading && !error && !uploads?.length) return null;

  const remove = async () => {
    setDeleting(true);
    try {
      await salesService.deleteUpload(toDelete.uploadId);
      notify(`${toDelete.fileName} removed`, 'info');
      onDeleted?.(toDelete.uploadId);
      setToDelete(null);
    } catch (err) {
      notify(err.message || 'The upload could not be removed.', 'error');
    } finally {
      setDeleting(false);
    }
  };

  return (
    <SectionCard title="Recent uploads" subtitle="Workbooks saved on the server for your company" noPadding>
      {error ? (
        <Stack direction="row" spacing={1} sx={{ p: 2.5, alignItems: 'center' }}>
          <Typography variant="body2" color="error">
            Unable to load previous uploads.
          </Typography>
          <Button size="small" onClick={onReload}>
            Retry
          </Button>
        </Stack>
      ) : loading && !uploads ? (
        <Box sx={{ p: 2 }}>
          {[0, 1].map((i) => (
            <Skeleton key={i} height={52} />
          ))}
        </Box>
      ) : (
        <Box component="ul" sx={{ listStyle: 'none', m: 0, p: 0 }}>
          {uploads.slice(0, 10).map((u) => {
            const current = u.uploadId === currentUploadId;
            return (
              <Stack
                component="li"
                key={u.uploadId}
                direction={{ xs: 'column', sm: 'row' }}
                spacing={1.5}
                sx={{ px: 2.5, py: 1.5, borderTop: 1, borderColor: 'divider', alignItems: { sm: 'center' }, '&:first-of-type': { borderTop: 0 } }}
              >
                <Stack direction="row" spacing={1.5} sx={{ alignItems: 'center', flexGrow: 1, minWidth: 0 }}>
                  <DescriptionOutlinedIcon color="action" />
                  <Box sx={{ minWidth: 0 }}>
                    <Typography variant="subtitle2" sx={{ wordBreak: 'break-all' }}>
                      {u.fileName}
                    </Typography>
                    <Typography variant="caption" component="div">
                      {formatDate(u.uploadedAt, { withTime: true })} · {u.uploadedBy} · {formatNumber(u.validRows)} of{' '}
                      {formatNumber(u.totalRows)} rows used
                      {u.columnCount ? ` · ${u.columnCount} columns` : ''}
                      {u.sheetName ? ` · sheet "${u.sheetName}"` : ''} · {formatFileSize(u.fileSize)}
                    </Typography>
                  </Box>
                </Stack>
                <Stack direction="row" spacing={1} sx={{ alignItems: 'center', flexShrink: 0 }}>
                  {current ? (
                    <Chip size="small" color="success" variant="outlined" label="Open" />
                  ) : (
                    <Button size="small" variant="outlined" onClick={() => onOpen(u.uploadId)} disabled={opening}>
                      Open
                    </Button>
                  )}
                  <Tooltip title={`Download ${u.originalFileName || u.fileName}`}>
                    <IconButton
                      size="small"
                      component="a"
                      href={salesService.originalFileUrl(u.uploadId)}
                      download={u.originalFileName || undefined}
                      aria-label={`Download original ${u.originalFileName || u.fileName}`}
                    >
                      <DownloadRoundedIcon fontSize="small" />
                    </IconButton>
                  </Tooltip>
                  <Tooltip title="Delete upload">
                    <IconButton size="small" aria-label={`Delete ${u.fileName}`} onClick={() => setToDelete(u)}>
                      <DeleteOutlineRoundedIcon fontSize="small" />
                    </IconButton>
                  </Tooltip>
                </Stack>
              </Stack>
            );
          })}
        </Box>
      )}

      <Dialog open={Boolean(toDelete)} onClose={() => !deleting && setToDelete(null)}>
        <DialogTitle>Delete this upload?</DialogTitle>
        <DialogContent>
          <DialogContentText>
            {toDelete?.fileName} and its {formatNumber(toDelete?.validRows || 0)} rows will no longer be available for analysis.
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setToDelete(null)} disabled={deleting}>
            Cancel
          </Button>
          <Button color="error" variant="contained" onClick={remove} disabled={deleting}>
            Delete
          </Button>
        </DialogActions>
      </Dialog>
    </SectionCard>
  );
}
