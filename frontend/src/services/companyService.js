// Company data through the API (/api/v1/companies/me).
import { api } from '@/lib/apiClient';

const companyService = {
  /** @returns {Promise<import('@/types/company').Company>} */
  getCompanyDetails() {
    return api.get('/companies/me');
  },

  /**
   * The company's sector and its sub-sectors ({ sector, sub_sectors }), or null when the company
   * has no sector configured.
   */
  async getCompanySectorDefinition() {
    try {
      return await api.get('/companies/me/sector');
    } catch (error) {
      if (error.status === 404) return null;
      throw error;
    }
  },
};

export default companyService;
