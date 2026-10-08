'use client';

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import authService from '@/services/authService';
import companyService from '@/services/companyService';
import { onAuthExpired } from '@/lib/apiClient';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  // verified: the API confirmed the session (a cached profile alone is not proof of a valid session).
  const [state, setState] = useState({ status: 'loading', user: null, verified: false });
  const [companyState, setCompanyState] = useState({ company: null, sectorDefinition: null, companyId: null });

  useEffect(() => {
    let active = true;
    const cached = authService.getStoredSession();
    if (cached) setState({ status: 'authenticated', user: cached.user, verified: false });

    // The httpOnly cookies are the source of truth; confirm them with the API.
    authService
      .getSession()
      .then((session) => {
        if (!active) return;
        setState(
          session
            ? { status: 'authenticated', user: session.user, verified: true }
            : { status: 'unauthenticated', user: null, verified: true },
        );
      })
      .catch(() => {
        // API unreachable: keep a cached profile (pages show their own errors), otherwise sign out.
        if (active && !cached) setState({ status: 'unauthenticated', user: null, verified: false });
      });
    return () => {
      active = false;
    };
  }, []);

  // A request got 401 even after a refresh attempt: the session is gone.
  useEffect(
    () =>
      onAuthExpired(() => {
        authService.clearStoredSession();
        setState({ status: 'unauthenticated', user: null, verified: true });
      }),
    [],
  );

  // Company details + sector (scopes the dealer Sector / Sub-sector filters) for the signed-in user.
  const companyId = state.user?.companyId ?? null;
  useEffect(() => {
    if (!companyId) return undefined;
    let active = true;
    Promise.all([companyService.getCompanyDetails(), companyService.getCompanySectorDefinition()])
      .then(([company, sectorDefinition]) => {
        if (active) setCompanyState({ company, sectorDefinition, companyId });
      })
      .catch(() => {
        /* header falls back to the user's details; pages that need the company show their own errors */
      });
    return () => {
      active = false;
    };
  }, [companyId]);

  const login = useCallback(async (credentials) => {
    const session = await authService.login(credentials);
    setState({ status: 'authenticated', user: session.user, verified: true });
    return session;
  }, []);

  const logout = useCallback(async () => {
    try {
      await authService.logout();
    } finally {
      setState({ status: 'unauthenticated', user: null, verified: true });
      setCompanyState({ company: null, sectorDefinition: null, companyId: null });
    }
  }, []);

  const updateUser = useCallback((user) => setState((prev) => ({ ...prev, user })), []);

  // After the company profile was edited: show the new details and reload the sector (it may have changed).
  const updateCompany = useCallback(
    (company) => {
      setCompanyState((prev) => ({ ...prev, company }));
      companyService
        .getCompanySectorDefinition()
        .then((sectorDefinition) => setCompanyState((prev) => ({ ...prev, company, sectorDefinition })))
        .catch(() => {});
    },
    [],
  );

  const value = useMemo(() => {
    const current = companyState.companyId === companyId;
    return {
      ...state,
      company: current ? companyState.company : null,
      sectorDefinition: current ? companyState.sectorDefinition : null,
      login,
      logout,
      updateUser,
      updateCompany,
    };
  }, [state, companyState, companyId, login, logout, updateUser, updateCompany]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used inside <AuthProvider>.');
  return context;
}
