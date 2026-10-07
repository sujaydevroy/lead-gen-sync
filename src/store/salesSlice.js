// Sales workspace state. Lives in the Redux store above every page, so uploaded
// Excel data, generated charts and selections survive menu navigation. Nothing is
// persisted to browser storage: a full page refresh starts with an empty workspace
// (uploads are stored by the API and can be reopened from "Recent uploads").
import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import salesService from '@/services/salesService';
import { DEFAULT_FX_RATES_TO_USD } from '@/lib/fx';
import { createDefaultSalesFilters } from '@/types/sales';

const initialState = {
  status: 'idle', // idle | processing | ready | error
  error: null,
  /** Id of the upload on the server (GET /sales/uploads/{id}) */
  uploadId: null,
  /** Raw sheet content as uploaded: { headers: string[], rows: any[][] } */
  uploadedData: null,
  /** Normalised SalesRecord[] (the Excel → JSON conversion) */
  processedData: [],
  fileMetadata: null,
  /** Chart datasets derived from processedData + filters, with the key they were built for */
  chartData: null,
  chartDataKey: '',
  chartConfig: {
    fxRates: DEFAULT_FX_RATES_TO_USD,
    fxStatus: 'idle', // idle | loading | loaded | error — rates from GET /sales/exchange-rates
    fxAsOf: null,
    fxOverridden: [],
    monthlyChart: 'bar', // bar | line
    tableSearch: '',
    tablePage: 0,
    tablePageSize: 10,
    activeView: 'charts', // charts | table | json
  },
  /** Shared by Upload Sales and Sales Forecast pages */
  filters: createDefaultSalesFilters(),
  forecast: { scenario: 'base' },
};

const parseFile = createAsyncThunk('sales/parseFile', async (file, { rejectWithValue }) => {
  try {
    return await salesService.parseSalesFile(file);
  } catch (error) {
    return rejectWithValue(error.message || 'The file could not be processed.');
  }
});

const loadSample = createAsyncThunk('sales/loadSample', async (_, { rejectWithValue }) => {
  try {
    return await salesService.loadSampleFile();
  } catch (error) {
    return rejectWithValue(error.message || 'The sample file could not be processed.');
  }
});

const openUpload = createAsyncThunk('sales/openUpload', async (uploadId, { rejectWithValue }) => {
  try {
    return await salesService.openUpload(uploadId);
  } catch (error) {
    return rejectWithValue(error.message || 'The upload could not be opened.');
  }
});

/** Company exchange rates from the API (global defaults + company overrides). */
export const loadExchangeRates = createAsyncThunk('sales/loadExchangeRates', () => salesService.getExchangeRates());
/** Save company overrides (administrators only). */
export const saveExchangeRates = createAsyncThunk('sales/saveExchangeRates', (rates) => salesService.saveExchangeRates(rates));
/** Remove company overrides (administrators only). */
export const resetExchangeRates = createAsyncThunk('sales/resetExchangeRates', () => salesService.resetExchangeRates());

const applyServerRates = (state, action) => {
  state.chartConfig.fxRates = action.payload.rates;
  state.chartConfig.fxAsOf = action.payload.asOf;
  state.chartConfig.fxOverridden = action.payload.overridden;
  state.chartConfig.fxStatus = 'loaded';
};

const salesSlice = createSlice({
  name: 'sales',
  initialState,
  reducers: {
    setUploadedData(state, action) {
      state.uploadedData = action.payload;
    },
    setProcessedData(state, action) {
      state.processedData = action.payload;
    },
    setFileMetadata(state, action) {
      state.fileMetadata = action.payload;
    },
    setChartData(state, action) {
      state.chartData = action.payload.data;
      state.chartDataKey = action.payload.key;
    },
    setChartConfig(state, action) {
      Object.assign(state.chartConfig, action.payload);
    },
    setFxRate(state, action) {
      const { currency, rate } = action.payload;
      state.chartConfig.fxRates = { ...state.chartConfig.fxRates, [currency]: rate };
    },
    resetFxRates(state) {
      state.chartConfig.fxRates = DEFAULT_FX_RATES_TO_USD;
    },
    setFilters(state, action) {
      Object.assign(state.filters, action.payload);
      state.chartConfig.tablePage = 0;
    },
    resetFilters(state) {
      state.filters = createDefaultSalesFilters();
      state.chartConfig.tablePage = 0;
    },
    setForecastScenario(state, action) {
      state.forecast.scenario = action.payload;
    },
    clearSalesData() {
      return initialState;
    },
  },
  extraReducers: (builder) => {
    const pending = (state) => {
      state.status = 'processing';
      state.error = null;
    };
    const fulfilled = (state, action) => {
      // A new upload replaces the previous dataset completely; keep only the exchange-rate table.
      const { fxRates, fxStatus, fxAsOf, fxOverridden } = state.chartConfig;
      Object.assign(state, initialState, {
        status: 'ready',
        uploadId: action.payload.uploadId ?? null,
        uploadedData: action.payload.uploadedData,
        processedData: action.payload.processedData,
        fileMetadata: action.payload.fileMetadata,
        chartConfig: { ...initialState.chartConfig, fxRates, fxStatus, fxAsOf, fxOverridden },
      });
    };
    const rejected = (state, action) => {
      // Keep any previously loaded dataset visible; only report the error.
      state.status = state.processedData.length ? 'ready' : 'error';
      state.error = action.payload || action.error.message;
    };
    builder
      .addCase(parseFile.pending, pending)
      .addCase(parseFile.fulfilled, fulfilled)
      .addCase(parseFile.rejected, rejected)
      .addCase(loadSample.pending, pending)
      .addCase(loadSample.fulfilled, fulfilled)
      .addCase(loadSample.rejected, rejected)
      .addCase(openUpload.pending, pending)
      .addCase(openUpload.fulfilled, fulfilled)
      .addCase(openUpload.rejected, rejected)
      .addCase(loadExchangeRates.pending, (state) => {
        state.chartConfig.fxStatus = 'loading';
      })
      .addCase(loadExchangeRates.fulfilled, applyServerRates)
      .addCase(loadExchangeRates.rejected, (state) => {
        state.chartConfig.fxStatus = 'error'; // keep the built-in indicative defaults
      })
      .addCase(saveExchangeRates.fulfilled, applyServerRates)
      .addCase(resetExchangeRates.fulfilled, applyServerRates);
  },
});

export const {
  setUploadedData,
  setProcessedData,
  setFileMetadata,
  setChartData,
  setChartConfig,
  setFxRate,
  resetFxRates,
  setFilters,
  resetFilters,
  setForecastScenario,
  clearSalesData,
} = salesSlice.actions;

export { parseFile as uploadSalesFile, loadSample as loadSampleSales, openUpload as openSalesUpload };

export const selectSales = (state) => state.sales;
export const selectHasSalesData = (state) => state.sales.processedData.length > 0;

export default salesSlice.reducer;
