'use client';

import { useState } from 'react';
import { Provider } from 'react-redux';
import { makeStore } from './index';

/** One store per browser page load — created once and kept for the page's lifetime. */
export default function StoreProvider({ children }) {
  const [store] = useState(makeStore);
  return <Provider store={store}>{children}</Provider>;
}
