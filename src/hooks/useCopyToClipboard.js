import { useCallback } from 'react';
import { useNotify } from '@/components/providers/NotificationProvider';

export default function useCopyToClipboard() {
  const notify = useNotify();
  return useCallback(
    async (text, label = 'Text') => {
      try {
        await navigator.clipboard.writeText(text);
        notify(`${label} copied to clipboard`, 'success');
      } catch {
        notify(`Could not copy ${label.toLowerCase()}. Your browser blocked clipboard access.`, 'error');
      }
    },
    [notify],
  );
}
