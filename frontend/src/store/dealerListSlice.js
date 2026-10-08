// Dealer list UI state (search, applied filters, pagination). Kept in Redux so the
// list is restored exactly when returning from a dealer's detail page.
import { createSlice } from '@reduxjs/toolkit';
import { createEmptyDealerFilters } from '@/types/dealer';

const initialState = {
  search: '',
  filters: createEmptyDealerFilters(),
  page: 1,
  pageSize: null, // null -> use the Settings default
};

const dealerListSlice = createSlice({
  name: 'dealerList',
  initialState,
  reducers: {
    setSearch(state, action) {
      state.search = action.payload;
      state.page = 1;
    },
    setFilters(state, action) {
      state.filters = { ...createEmptyDealerFilters(), ...action.payload };
      state.page = 1;
    },
    removeFilterValue(state, action) {
      const { group, value } = action.payload;
      state.filters[group] = state.filters[group].filter((v) => v !== value);
      state.page = 1;
    },
    /** Clears filters and search (empty-state "Clear Filters"). */
    clearFilters(state) {
      state.filters = createEmptyDealerFilters();
      state.search = '';
      state.page = 1;
    },
    /** Clears the sidebar filter groups but keeps the search text. */
    clearFilterGroups(state) {
      state.filters = createEmptyDealerFilters();
      state.page = 1;
    },
    setPage(state, action) {
      state.page = action.payload;
    },
    setPageSize(state, action) {
      state.pageSize = action.payload;
      state.page = 1;
    },
  },
});

export const { setSearch, setFilters, removeFilterValue, clearFilters, clearFilterGroups, setPage, setPageSize } =
  dealerListSlice.actions;
export default dealerListSlice.reducer;
