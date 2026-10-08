'use client';

import { useEffect, useRef } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import {
  accountSignedOut,
  DEV_SETTINGS_STORAGE_KEY,
  hydrateAccountSettings,
  hydrateDevSettings,
  pickAccountSettings,
} from '@/store/settingsSlice';
import { configureDevNetwork } from '@/lib/apiClient';
import settingsService from '@/services/settingsService';
import { useAuth } from './AuthProvider';
import { useNotify } from './NotificationProvider';

const SAVE_DELAY_MS = 500;

/**
 * Loads account settings from the API after sign-in and saves changes back (debounced);
 * keeps the browser-only developer options in localStorage and applies them to the API client.
 */
export default function SettingsSync() {
  const dispatch = useDispatch();
  const notify = useNotify();
  const { user } = useAuth();
  const settings = useSelector((state) => state.settings);
  const lastSaved = useRef(null);
  const userId = user?.id ?? null;

  // Developer options: browser-only.
  useEffect(() => {
    let stored = {};
    try {
      stored = JSON.parse(window.localStorage.getItem(DEV_SETTINGS_STORAGE_KEY) || '{}');
      window.localStorage.removeItem('dcp.settings'); // pre-API format
    } catch {
      stored = {};
    }
    dispatch(hydrateDevSettings({ simulateErrors: Boolean(stored.simulateErrors), extraLatencyMs: Number(stored.extraLatencyMs) || 0 }));
  }, [dispatch]);

  useEffect(() => {
    configureDevNetwork({ simulateErrors: settings.simulateErrors, extraLatencyMs: settings.extraLatencyMs });
    if (!settings.devLoaded) return;
    try {
      window.localStorage.setItem(
        DEV_SETTINGS_STORAGE_KEY,
        JSON.stringify({ simulateErrors: settings.simulateErrors, extraLatencyMs: settings.extraLatencyMs }),
      );
    } catch {
      /* storage unavailable — options last for this page only */
    }
  }, [settings.simulateErrors, settings.extraLatencyMs, settings.devLoaded]);

  // Account settings: load once per signed-in user.
  useEffect(() => {
    if (!userId) {
      lastSaved.current = null;
      dispatch(accountSignedOut());
      return undefined;
    }
    let active = true;
    settingsService
      .getSettings()
      .then((data) => {
        if (!active) return;
        lastSaved.current = JSON.stringify(pickAccountSettings(data));
        dispatch(hydrateAccountSettings(data));
      })
      .catch(() => {
        /* keep defaults; the next change will try to save again */
      });
    return () => {
      active = false;
    };
  }, [userId, dispatch]);

  // Save changes back to the API (debounced).
  const account = JSON.stringify(pickAccountSettings(settings));
  useEffect(() => {
    if (!userId || !settings.accountLoaded || account === lastSaved.current) return undefined;
    const timer = setTimeout(() => {
      settingsService
        .saveSettings(JSON.parse(account))
        .then((saved) => {
          lastSaved.current = JSON.stringify(pickAccountSettings(saved));
        })
        .catch((error) => notify(`Settings were not saved: ${error.message}`, 'error'));
    }, SAVE_DELAY_MS);
    return () => clearTimeout(timer);
  }, [account, userId, settings.accountLoaded, notify]);

  return null;
}
