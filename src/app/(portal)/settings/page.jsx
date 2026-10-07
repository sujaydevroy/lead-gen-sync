'use client';

import { useDispatch, useSelector } from 'react-redux';
import Grid from '@mui/material/Grid';
import Stack from '@mui/material/Stack';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Switch from '@mui/material/Switch';
import Select from '@mui/material/Select';
import MenuItem from '@mui/material/MenuItem';
import Slider from '@mui/material/Slider';
import Button from '@mui/material/Button';
import Divider from '@mui/material/Divider';
import Alert from '@mui/material/Alert';
import ToggleButton from '@mui/material/ToggleButton';
import ToggleButtonGroup from '@mui/material/ToggleButtonGroup';
import PageHeader from '@/components/ui/PageHeader';
import SectionCard from '@/components/ui/SectionCard';
import { useNotify } from '@/components/providers/NotificationProvider';
import { updateSettings, resetSettings } from '@/store/settingsSlice';
import { setPageSize } from '@/store/dealerListSlice';
import { PAGE_SIZE_OPTIONS } from '@/types/dealer';

function SettingRow({ title, description, control, id }) {
  return (
    <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2} sx={{ py: 2, alignItems: { sm: 'center' }, justifyContent: 'space-between' }}>
      <Box sx={{ maxWidth: 520 }}>
        <Typography variant="subtitle2" id={id}>
          {title}
        </Typography>
        <Typography variant="body2" color="text.secondary">
          {description}
        </Typography>
      </Box>
      <Box sx={{ flexShrink: 0 }}>{control}</Box>
    </Stack>
  );
}

export default function SettingsPage() {
  const dispatch = useDispatch();
  const notify = useNotify();
  const settings = useSelector((state) => state.settings);
  const set = (patch) => dispatch(updateSettings(patch));

  return (
    <>
      <PageHeader
        title="Settings"
        subtitle="Dealer list preferences are saved to your account; developer options stay in this browser"
        actions={
          <Button
            color="inherit"
            variant="outlined"
            onClick={() => {
              dispatch(resetSettings());
              dispatch(setPageSize(null));
              notify('Settings restored to defaults', 'info');
            }}
          >
            Reset to defaults
          </Button>
        }
      />

      <Grid container spacing={3}>
        <Grid size={{ xs: 12, lg: 7 }}>
          <SectionCard title="Dealer list">
            <Stack divider={<Divider flexItem />}>
              <SettingRow
                id="setting-page-size"
                title="Default page size"
                description="Number of dealers shown per page when you open the Dealers page."
                control={
                  <Select
                    size="small"
                    value={settings.defaultPageSize}
                    inputProps={{ 'aria-labelledby': 'setting-page-size' }}
                    onChange={(e) => {
                      set({ defaultPageSize: Number(e.target.value) });
                      dispatch(setPageSize(null));
                    }}
                  >
                    {PAGE_SIZE_OPTIONS.map((n) => (
                      <MenuItem key={n} value={n}>
                        {n} per page
                      </MenuItem>
                    ))}
                  </Select>
                }
              />
              <SettingRow
                id="setting-instant"
                title="Apply filters instantly"
                description="When off, filter changes are applied with the “Apply Filters” button."
                control={
                  <Switch
                    checked={settings.applyFiltersInstantly}
                    onChange={(e) => set({ applyFiltersInstantly: e.target.checked })}
                    slotProps={{ input: { 'aria-labelledby': 'setting-instant' } }}
                  />
                }
              />
              <SettingRow
                id="setting-view"
                title="Desktop layout"
                description="Show dealers as a table or as cards on larger screens. Phones always use cards."
                control={
                  <ToggleButtonGroup
                    size="small"
                    exclusive
                    value={settings.desktopDealerView}
                    onChange={(_, v) => v && set({ desktopDealerView: v })}
                    aria-labelledby="setting-view"
                  >
                    <ToggleButton value="table">Table</ToggleButton>
                    <ToggleButton value="cards">Cards</ToggleButton>
                  </ToggleButtonGroup>
                }
              />
            </Stack>
          </SectionCard>
        </Grid>
        <Grid size={{ xs: 12, lg: 5 }}>
          <SectionCard title="Developer options" subtitle="For testing the loading and error states (this browser only)">
            <Stack divider={<Divider flexItem />}>
              <SettingRow
                id="setting-errors"
                title="Simulate API errors"
                description="API requests (except sign-in) fail before they are sent, so you can see the error states."
                control={
                  <Switch
                    color="error"
                    checked={settings.simulateErrors}
                    onChange={(e) => set({ simulateErrors: e.target.checked })}
                    slotProps={{ input: { 'aria-labelledby': 'setting-errors' } }}
                  />
                }
              />
              <Box sx={{ py: 2 }}>
                <Typography variant="subtitle2" id="setting-latency">
                  Extra latency: {settings.extraLatencyMs} ms
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Delay added before every API request (skeleton loaders show during this time).
                </Typography>
                <Slider
                  value={settings.extraLatencyMs}
                  onChange={(_, v) => set({ extraLatencyMs: v })}
                  min={0}
                  max={3000}
                  step={50}
                  aria-labelledby="setting-latency"
                  sx={{ mt: 1 }}
                />
              </Box>
            </Stack>
            {settings.simulateErrors && (
              <Alert severity="warning" sx={{ mt: 1 }}>
                Error simulation is on — most pages will show their error state until you turn it off.
              </Alert>
            )}
          </SectionCard>
        </Grid>
      </Grid>
    </>
  );
}
