// System administration through the API (/api/v1/admin/*, role "System Administrator").
import { api, API_BASE, ApiError } from '@/lib/apiClient';

export const DEALER_FILE_EXTENSIONS = ['.xlsx', '.xls', '.csv', '.json'];
export const MAX_DEALER_FILE_BYTES = 10 * 1024 * 1024;

function validateDealerFile(file) {
  const name = (file.name || '').toLowerCase();
  if (![...DEALER_FILE_EXTENSIONS, '.xlsm'].some((ext) => name.endsWith(ext))) {
    throw new ApiError('Unsupported file type. Upload an Excel workbook (.xlsx, .xls), a .csv or a .json file.', 415);
  }
  if (file.size > MAX_DEALER_FILE_BYTES) throw new ApiError('The file is larger than 10 MB.', 413);
  if (file.size === 0) throw new ApiError('The file is empty.', 422);
}

const adminService = {
  /** { countries, regions, regionsByCountry: { India: [...] }, sectors, dealerTypes, dealerStatuses, currencies } */
  getLookups() {
    return api.get('/admin/lookups');
  },

  /** Customer companies with userCount / isActive (the platform company is excluded). */
  listCompanies({ search = '', includeInactive = true } = {}) {
    return api.get('/admin/companies', { search, includeInactive });
  },

  getCompany(companyId) {
    return api.get(`/admin/companies/${encodeURIComponent(companyId)}`);
  },

  /** values = company fields + admin: { name, email, jobTitle, phone, password } */
  createCompany(values) {
    return api.post('/admin/companies', values);
  },

  /** Replaces the whole editable profile. */
  updateCompany(companyId, values) {
    return api.put(`/admin/companies/${encodeURIComponent(companyId)}`, values);
  },

  deactivateCompany(companyId) {
    return api.delete(`/admin/companies/${encodeURIComponent(companyId)}`);
  },

  activateCompany(companyId) {
    return api.post(`/admin/companies/${encodeURIComponent(companyId)}/activate`);
  },

  /** Users of a company (read-only here; the company's own administrator manages them). */
  getCompanyUsers(companyId) {
    return api.get(`/admin/companies/${encodeURIComponent(companyId)}/users`);
  },

  /** changes = any of { name, email, jobTitle, phone, role } (only the fields sent change) */
  updateCompanyUser(companyId, userId, changes) {
    return api.patch(`/admin/companies/${encodeURIComponent(companyId)}/users/${encodeURIComponent(userId)}`, changes);
  },

  unlockCompanyUser(companyId, userId) {
    return api.post(`/admin/companies/${encodeURIComponent(companyId)}/users/${encodeURIComponent(userId)}/unlock`);
  },

  setCompanyUserPassword(companyId, userId, password) {
    return api.post(`/admin/companies/${encodeURIComponent(companyId)}/users/${encodeURIComponent(userId)}/password`, {
      password,
    });
  },

  /** { dealerCount } — active dealers in the dealer directory (dealers belong to no company). */
  getDealerDirectory() {
    return api.get('/admin/dealer-directory');
  },

  /**
   * Upload a dealer file into the dealer directory. The rows are saved in dcp.dealers; the response is the
   * outcome only: { inserted, updated, failed, issues: [{ row, message }], columnMapping, ignoredColumns,
   * createdLookups: { Country: [...], Region: [...], ... }, sourcesSaved, ... }
   */
  async uploadDealers(file) {
    validateDealerFile(file);
    const form = new FormData();
    form.append('file', file, file.name);
    return api.upload('/admin/dealer-uploads', form);
  },

  /** URL of the .xlsx upload template (headers, example row and allowed values). */
  dealerTemplateUrl() {
    return `${API_BASE}/admin/dealer-uploads/template`;
  },
};

export default adminService;
