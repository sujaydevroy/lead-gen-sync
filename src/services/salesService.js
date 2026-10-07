// Sales uploads and exchange rates through the API. The server parses the workbook, stores the
// rows and returns { uploadId, uploadedData, processedData, fileMetadata } — the shape the
// Redux sales workspace keeps.
import { api, API_BASE, ApiError } from '@/lib/apiClient';

export const ACCEPTED_EXTENSIONS = ['.xlsx'];
export const MAX_FILE_BYTES = 10 * 1024 * 1024;

/** Quick client-side checks so obvious mistakes don't need a round trip. */
function validateFile(file) {
  const name = (file.name || '').toLowerCase();
  if (!ACCEPTED_EXTENSIONS.some((ext) => name.endsWith(ext))) {
    throw new ApiError('Unsupported file type. Please upload an Excel .xlsx workbook.', 415);
  }
  if (file.size > MAX_FILE_BYTES) throw new ApiError('The file is larger than 10 MB.', 413);
  if (file.size === 0) throw new ApiError('The file is empty.', 422);
}

const salesService = {
  async parseSalesFile(file) {
    validateFile(file);
    const form = new FormData();
    form.append('file', file, file.name);
    return api.upload('/sales/uploads', form);
  },

  /** Loads the bundled demo workbook on the server (public/samples/sample_sales.xlsx). */
  loadSampleFile() {
    return api.post('/sales/uploads/sample');
  },

  /** Previously uploaded workbooks for the company (newest first). */
  listUploads() {
    return api.get('/sales/uploads');
  },

  openUpload(uploadId) {
    return api.get(`/sales/uploads/${uploadId}`);
  },

  deleteUpload(uploadId) {
    return api.delete(`/sales/uploads/${uploadId}`);
  },

  /** URL of the workbook exactly as uploaded (served by the API from its file storage). */
  originalFileUrl(uploadId) {
    return `${API_BASE}/sales/uploads/${uploadId}/file`;
  },

  /** The sheet's columns (header, Excel letter, recognised field) as stored by the API. */
  getUploadColumns(uploadId) {
    return api.get(`/sales/uploads/${uploadId}/columns`);
  },

  /** Stored sheet rows with all cells; valid=false returns the rejected rows. */
  getUploadRows(uploadId, { valid, page = 1, pageSize = 100 } = {}) {
    return api.get(`/sales/uploads/${uploadId}/rows`, { valid, page, pageSize });
  },

  /** { asOf, rates: { USD: 1, EUR: 1.08, ... }, overridden: [...] } */
  getExchangeRates() {
    return api.get('/sales/exchange-rates');
  },

  /** Company overrides (administrators only). */
  saveExchangeRates(rates) {
    return api.put('/sales/exchange-rates', { rates });
  },

  resetExchangeRates() {
    return api.delete('/sales/exchange-rates');
  },
};

export default salesService;
