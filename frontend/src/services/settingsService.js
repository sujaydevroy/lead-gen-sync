// Per-user preferences stored by the API (/api/v1/users/me/settings).
import { api } from '@/lib/apiClient';

const settingsService = {
  /** @returns {Promise<{ defaultPageSize: number, applyFiltersInstantly: boolean, desktopDealerView: 'table'|'cards' }>} */
  getSettings() {
    return api.get('/users/me/settings');
  },

  saveSettings({ defaultPageSize, applyFiltersInstantly, desktopDealerView }) {
    return api.put('/users/me/settings', { defaultPageSize, applyFiltersInstantly, desktopDealerView });
  },
};

export default settingsService;
