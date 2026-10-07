import { configureStore } from '@reduxjs/toolkit';
import salesReducer from './salesSlice';
import dealerListReducer from './dealerListSlice';
import settingsReducer from './settingsSlice';

export function makeStore() {
  return configureStore({
    reducer: {
      sales: salesReducer,
      dealerList: dealerListReducer,
      settings: settingsReducer,
    },
    middleware: (getDefaultMiddleware) =>
      getDefaultMiddleware({
        // Sales datasets can be large; keep dev checks but don't warn about their cost.
        immutableCheck: { warnAfter: 256 },
        // The upload thunk receives a File as its argument.
        serializableCheck: { warnAfter: 256, ignoredActionPaths: ['meta.arg'] },
      }),
  });
}
