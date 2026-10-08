import { useSelector } from 'react-redux';
import dealerService from '@/services/dealerService';
import useAsync from './useAsync';

/** Fetches the current page of dealers for the filters/search/pagination held in Redux. */
export default function useDealerList() {
  const { search, filters, page, pageSize: chosenPageSize } = useSelector((state) => state.dealerList);
  const defaultPageSize = useSelector((state) => state.settings.defaultPageSize);
  const pageSize = chosenPageSize || defaultPageSize;

  const query = useAsync(
    () => dealerService.getDealers({ search, filters, page, pageSize }),
    [search, JSON.stringify(filters), page, pageSize],
  );

  return { ...query, search, filters, page, pageSize };
}
