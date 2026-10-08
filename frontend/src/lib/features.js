// Feature switches. The demo keeps things simple: each company has one user (see the API's 1:1 mapping),
// so company-level user management is switched off. The code stays; set a flag to true to bring it back.

export const FEATURES = {
  /** "Users" page where a Company Administrator adds users, changes roles, activates / deactivates. */
  companyUserManagement: false,
};
