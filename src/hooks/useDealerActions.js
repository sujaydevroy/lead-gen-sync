import { useCallback } from 'react';
import { useAuth } from '@/components/providers/AuthProvider';
import { useNotify } from '@/components/providers/NotificationProvider';
import communicationService from '@/services/communicationService';
import { hasValue } from '@/types/dealer';
import useCopyToClipboard from './useCopyToClipboard';

/** Email / call / copy actions for a dealer. Email and call are logged in the dealer's history. */
export default function useDealerActions() {
  const { user } = useAuth();
  const notify = useNotify();
  const copy = useCopyToClipboard();

  const sendEmail = useCallback(
    (dealer) => {
      if (!hasValue(dealer.email)) return notify('This dealer has no email address on file.', 'warning');
      window.location.href = `mailto:${dealer.email}`;
      communicationService
        .logInteraction({ dealerId: dealer.dealer_id, type: 'Email', subject: 'Email opened in mail client', sender: user?.name })
        .then(() => notify(`Opening your email client for ${dealer.dealer_name}. Logged in history.`, 'info'));
    },
    [notify, user],
  );

  const call = useCallback(
    (dealer) => {
      if (!hasValue(dealer.phone)) return notify('This dealer has no phone number on file.', 'warning');
      window.location.href = `tel:${dealer.phone.replace(/[^\d+]/g, '')}`;
      communicationService
        .logInteraction({ dealerId: dealer.dealer_id, type: 'Call', subject: `Call to ${dealer.phone}`, sender: user?.name })
        .then(() => notify(`Calling ${dealer.phone}. Logged in history.`, 'info'));
    },
    [notify, user],
  );

  const copyEmail = useCallback(
    (dealer) => (hasValue(dealer.email) ? copy(dealer.email, 'Email') : notify('No email address on file.', 'warning')),
    [copy, notify],
  );
  const copyPhone = useCallback(
    (dealer) => (hasValue(dealer.phone) ? copy(dealer.phone, 'Phone number') : notify('No phone number on file.', 'warning')),
    [copy, notify],
  );

  return { sendEmail, call, copyEmail, copyPhone };
}
