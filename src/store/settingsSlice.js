// User preferences.
// - Account settings (page size, instant filters, desktop layout) are stored by the API per user.
// - Developer options (simulated errors / extra latency) stay in this browser's localStorage.
// <SettingsSync /> loads and saves both.
import { createSlice } from '@reduxjs/toolkit';

export const DEV_SETTINGS_STORAGE_KEY = 'dcp.devSettings';

export const defaultAccountSettings = {
  defaultPageSize: 20,
  applyFiltersInstantly: true,
  desktopDealerView: 'table', // table | cards
};

export const defaultDevSettings = {
  simulateErrors: false,
  extraLatencyMs: 0,
};

export const pickAccountSettings = (state) => ({
  defaultPageSize: state.defaultPageSize,
  applyFiltersInstantly: state.applyFiltersInstantly,
  desktopDealerView: state.desktopDealerView,
});

const settingsSlice = createSlice({
  name: 'settings',
  initialState: { ...defaultAccountSettings, ...defaultDevSettings, devLoaded: false, accountLoaded: false },
  reducers: {
    hydrateDevSettings(state, action) {
      Object.assign(state, defaultDevSettings, action.payload, { devLoaded: true });
    },
    hydrateAccountSettings(state, action) {
      Object.assign(state, pickAccountSettings({ ...defaultAccountSettings, ...action.payload }), { accountLoaded: true });
    },
    accountSignedOut(state) {
      Object.assign(state, defaultAccountSettings, { accountLoaded: false });
    },
    updateSettings(state, action) {
      Object.assign(state, action.payload);
    },
    resetSettings(state) {
      Object.assign(state, defaultAccountSettings, defaultDevSettings);
    },
  },
});

export const { hydrateDevSettings, hydrateAccountSettings, accountSignedOut, updateSettings, resetSettings } =
  settingsSlice.actions;
export default settingsSlice.reducer;
