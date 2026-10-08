// Dealer data access through the API (/api/v1/dealers, /lookups, /dashboard).
// Filtering, facet counts and pagination happen on the server; the response shape is
// { items, total, page, pageSize, totalPages, facets, totalDealers }.
import { api } from '@/lib/apiClient';
import { createEmptyDealerFilters } from '@/types/dealer';

const dealerService = {
  /** @param {import('@/types/dealer').DealerQuery & { signal?: AbortSignal }} query */
  getDealers({ search = '', filters = createEmptyDealerFilters(), page = 1, pageSize = 20, signal } = {}) {
    return api.get(
      '/dealers',
      {
        search: search.trim(),
        countries: filters.countries,
        regions: filters.regions,
        statuses: filters.statuses,
        types: filters.types,
        sectors: filters.sectors,
        subSectors: filters.subSectors,
        page,
        pageSize,
      },
      { signal },
    );
  },

  /** @returns {Promise<import('@/types/dealer').Dealer>} */
  getDealerById(dealerId) {
    return api.get(`/dealers/${encodeURIComponent(dealerId)}`);
  },

  /** Lightweight lookup for pickers / autocomplete. */
  searchDealers(term, limit = 20) {
    return api.get('/dealers/search', { q: term, limit });
  },

  getRecentDealers(limit = 5) {
    return api.get('/dealers/recent', { limit });
  },

  async getDealerStats() {
    const stats = await api.get('/dashboard/stats');
    return stats.dealers;
  },

  getCountries() {
    return api.get('/lookups/countries');
  },

  /** @param {string | string[]} [country] one or more countries; omit for all regions */
  getRegions(country) {
    return api.get('/lookups/regions', { country: country ? [].concat(country) : undefined });
  },
};

export default dealerService;
