// User management for Company Administrators (/api/v1/users), limited to their own company.
import { api } from '@/lib/apiClient';

const companyUserService = {
  /** All users of the company, including inactive ones. */
  listUsers() {
    return api.get('/users');
  },

  /** Roles an administrator can assign (Company Administrator, Sales Manager, ...). */
  listRoles() {
    return api.get('/users/roles');
  },

  /** values = { name, email, jobTitle, phone, role, password } (password = temporary password) */
  createUser(values) {
    return api.post('/users', values);
  },

  /** changes = any of { name, email, jobTitle, phone, role, isActive } (only the fields sent change) */
  updateUser(userId, changes) {
    return api.patch(`/users/${encodeURIComponent(userId)}`, changes);
  },

  unlockUser(userId) {
    return api.post(`/users/${encodeURIComponent(userId)}/unlock`);
  },

  setPassword(userId, password) {
    return api.post(`/users/${encodeURIComponent(userId)}/password`, { password });
  },
};

export default companyUserService;
