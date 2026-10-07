// Communication history and messaging through the API.
// subscribe() lets open views refetch after this tab sends a message or logs an interaction.
import { api } from '@/lib/apiClient';

const listeners = new Set();
const emit = () => listeners.forEach((listener) => listener());

const communicationService = {
  /** Subscribe to changes made from this tab. Returns an unsubscribe fn. */
  subscribe(listener) {
    listeners.add(listener);
    return () => listeners.delete(listener);
  },

  /**
   * One page of communications (newest first).
   * @param {{ dealerId?: string, types?: string[], direction?: 'inbound'|'outbound'|'', search?: string,
   *           page?: number, pageSize?: number }} [query]
   * @returns {Promise<{ items: import('@/types/communication').Communication[], total: number, page: number,
   *                     pageSize: number, totalPages: number }>}
   */
  getCommunicationsPage({ dealerId, types, direction, search, page = 1, pageSize = 50 } = {}) {
    return api.get('/communications', { dealerId, types, direction, search, page, pageSize });
  },

  /** Full history for one dealer (up to 200 most recent items). */
  async getCommunicationHistory({ dealerId, types, direction, search } = {}) {
    const result = await communicationService.getCommunicationsPage({ dealerId, types, direction, search, pageSize: 200 });
    return result.items;
  },

  getRecentCommunications(limit = 6) {
    return api.get('/communications/recent', { limit });
  },

  getCommunicationStats() {
    return api.get('/communications/stats');
  },

  /**
   * Send a portal message to a dealer (multipart, optional attachment).
   * @param {{ dealerId: string, subject: string, message: string, attachment?: File | null }} payload
   */
  async sendMessage({ dealerId, subject, message, attachment }) {
    const form = new FormData();
    form.append('subject', subject);
    form.append('message', message);
    if (attachment) form.append('attachment', attachment, attachment.name);
    const saved = await api.upload(`/dealers/${encodeURIComponent(dealerId)}/messages`, form);
    emit();
    return saved;
  },

  /**
   * Record an interaction started outside the portal (email client, phone call).
   * @param {{ dealerId: string, type: 'Email'|'Call', subject: string }} payload
   */
  async logInteraction({ dealerId, type, subject }) {
    const saved = await api.post(`/dealers/${encodeURIComponent(dealerId)}/interactions`, { type, subject });
    emit();
    return saved;
  },
};

export default communicationService;
