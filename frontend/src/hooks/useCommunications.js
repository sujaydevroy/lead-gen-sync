import { useEffect } from 'react';
import communicationService from '@/services/communicationService';
import useAsync from './useAsync';

/** Communication history that refreshes automatically when a message is sent or logged. */
export default function useCommunications(query = {}) {
  const key = JSON.stringify(query);
  const result = useAsync(() => communicationService.getCommunicationHistory(query), [key]);
  const { reload } = result;
  useEffect(() => communicationService.subscribe(reload), [reload]);
  return result;
}
