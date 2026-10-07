import { useEffect } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { loadExchangeRates } from '@/store/salesSlice';

/** Loads the company's exchange rates from the API once per page session. */
export default function useExchangeRates() {
  const dispatch = useDispatch();
  const status = useSelector((state) => state.sales.chartConfig.fxStatus);
  useEffect(() => {
    if (status === 'idle') dispatch(loadExchangeRates());
  }, [status, dispatch]);
  return status;
}
