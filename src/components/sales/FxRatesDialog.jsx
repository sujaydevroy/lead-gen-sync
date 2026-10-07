'use client';

import { useState } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import Dialog from '@mui/material/Dialog';
import DialogTitle from '@mui/material/DialogTitle';
import DialogContent from '@mui/material/DialogContent';
import DialogActions from '@mui/material/DialogActions';
import Button from '@mui/material/Button';
import TextField from '@mui/material/TextField';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';
import Alert from '@mui/material/Alert';
import CircularProgress from '@mui/material/CircularProgress';
import { useAuth } from '@/components/providers/AuthProvider';
import { useNotify } from '@/components/providers/NotificationProvider';
import { loadExchangeRates, resetExchangeRates, saveExchangeRates, setFxRate } from '@/store/salesSlice';
import { formatDate } from '@/lib/format';

const ADMIN_ROLE = 'Company Administrator';

/**
 * USD conversion rates used when analysing "All currencies".
 * Administrators save company rates through the API; other users can adjust rates for this session only.
 */
export default function FxRatesDialog({ open, onClose, currencies }) {
  const dispatch = useDispatch();
  const notify = useNotify();
  const { user } = useAuth();
  const { fxRates: rates, fxAsOf, fxOverridden, fxStatus } = useSelector((state) => state.sales.chartConfig);
  const [draft, setDraft] = useState({});
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const isAdmin = user?.role === ADMIN_ROLE;

  const list = [...new Set([...Object.keys(rates), ...currencies.filter((c) => c !== 'N/A')])].sort();
  const valueFor = (c) => (draft[c] !== undefined ? draft[c] : rates[c] ?? '');
  const invalid = list.some((c) => {
    const v = valueFor(c);
    return v !== '' && !(Number(v) > 0);
  });
  const changes = Object.fromEntries(
    Object.entries(draft)
      .filter(([c, v]) => v !== '' && Number(v) > 0 && Number(v) !== rates[c])
      .map(([c, v]) => [c, Number(v)]),
  );

  const close = () => {
    setDraft({});
    setError('');
    onClose();
  };

  const run = async (action, message) => {
    setSaving(true);
    setError('');
    try {
      await dispatch(action).unwrap();
      notify(message, 'success');
      close();
    } catch (err) {
      setError(err?.message || 'The exchange rates could not be saved.');
    } finally {
      setSaving(false);
    }
  };

  const save = () => {
    if (!Object.keys(changes).length) return close();
    if (isAdmin) return run(saveExchangeRates(changes), 'Company exchange rates saved');
    Object.entries(changes).forEach(([currency, rate]) => dispatch(setFxRate({ currency, rate })));
    notify('Rates applied for this session', 'info');
    return close();
  };

  const restore = () =>
    isAdmin
      ? run(resetExchangeRates(), 'Company rates removed; default rates restored')
      : run(loadExchangeRates(), 'Default rates restored for this session');

  return (
    <Dialog open={open} onClose={close} fullWidth maxWidth="xs">
      <DialogTitle>Exchange rates</DialogTitle>
      <DialogContent dividers>
        <Alert severity="info" sx={{ mb: 2 }}>
          USD value of one unit of each currency, used only to combine currencies when &quot;All currencies&quot; is selected.
          {fxStatus === 'loaded' && fxAsOf ? ` Rates effective ${formatDate(fxAsOf)}.` : ''}
          {fxStatus === 'error' ? ' The server rates could not be loaded; built-in indicative rates are shown.' : ''}
          {isAdmin
            ? ' Saving updates the rates for your whole company.'
            : ' Only administrators can change company rates; your edits apply to this session only.'}
        </Alert>
        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}
        <Stack spacing={1.5}>
          {list.map((c) => {
            const v = valueFor(c);
            const bad = v !== '' && !(Number(v) > 0);
            return (
              <Stack key={c} direction="row" spacing={2} sx={{ alignItems: 'center' }}>
                <Typography sx={{ width: 64, fontWeight: 600 }}>1 {c}</Typography>
                <Typography color="text.secondary">=</Typography>
                <TextField
                  size="small"
                  type="number"
                  value={v}
                  disabled={c === 'USD' || saving}
                  onChange={(e) => setDraft((d) => ({ ...d, [c]: e.target.value }))}
                  error={bad}
                  helperText={
                    bad
                      ? 'Must be greater than 0'
                      : rates[c] === undefined && v === ''
                        ? 'No rate — rows excluded'
                        : fxOverridden.includes(c)
                          ? 'Company rate'
                          : undefined
                  }
                  slotProps={{ htmlInput: { min: 0, step: 'any', 'aria-label': `USD per ${c}` } }}
                  sx={{ flexGrow: 1 }}
                />
                <Typography color="text.secondary">USD</Typography>
              </Stack>
            );
          })}
        </Stack>
      </DialogContent>
      <DialogActions>
        <Button color="inherit" onClick={restore} disabled={saving || (isAdmin && !fxOverridden.length)}>
          Restore defaults
        </Button>
        <Button onClick={close} disabled={saving}>
          Cancel
        </Button>
        <Button
          variant="contained"
          onClick={save}
          disabled={invalid || saving}
          startIcon={saving ? <CircularProgress size={16} color="inherit" /> : null}
        >
          {isAdmin ? 'Save company rates' : 'Apply'}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
