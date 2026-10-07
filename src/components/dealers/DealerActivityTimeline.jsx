'use client';

import { useMemo } from 'react';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Skeleton from '@mui/material/Skeleton';
import VerifiedOutlinedIcon from '@mui/icons-material/VerifiedOutlined';
import AddBusinessOutlinedIcon from '@mui/icons-material/AddBusinessOutlined';
import ReceiptLongOutlinedIcon from '@mui/icons-material/ReceiptLongOutlined';
import { TYPE_ICONS, describeCommunication } from '@/components/communication/CommunicationHistory';
import EmptyState from '@/components/ui/EmptyState';
import { hasValue } from '@/types/dealer';
import { formatCurrency, formatDate, formatRelativeTime } from '@/lib/format';

/** Merges communications with dealer lifecycle events into one chronological timeline. */
export default function DealerActivityTimeline({ dealer, communications, loading }) {
  const events = useMemo(() => {
    const list = (communications || []).map((c) => ({
      id: c.id,
      date: c.createdAt,
      Icon: TYPE_ICONS[c.type],
      title: describeCommunication(c),
      detail: `${c.type} · ${c.subject} · ${c.status}`,
      tone: c.direction === 'inbound' ? 'primary.main' : 'success.main',
    }));
    if (hasValue(dealer.last_transaction_date)) {
      const amount = Number(dealer.last_transaction_amount);
      list.push({
        id: 'txn',
        date: dealer.last_transaction_date,
        Icon: ReceiptLongOutlinedIcon,
        title: 'Last recorded transaction',
        detail: Number.isFinite(amount) && hasValue(dealer.currency) ? formatCurrency(amount, dealer.currency) : 'Amount not available',
        tone: 'warning.main',
      });
    }
    if (hasValue(dealer.verification_date)) {
      list.push({
        id: 'verified',
        date: dealer.verification_date,
        Icon: VerifiedOutlinedIcon,
        title: 'Dealer details verified',
        detail: hasValue(dealer.source_url) ? `Source: ${dealer.source_url}` : 'Verified record',
        tone: 'secondary.main',
      });
    }
    if (hasValue(dealer.created_at)) {
      list.push({ id: 'created', date: dealer.created_at, Icon: AddBusinessOutlinedIcon, title: 'Dealer added to the portal', detail: dealer.dealer_id, tone: 'text.secondary' });
    }
    return list.sort((a, b) => new Date(b.date) - new Date(a.date));
  }, [dealer, communications]);

  if (loading && !communications) {
    return [0, 1, 2, 3].map((i) => <Skeleton key={i} height={56} />);
  }
  if (!events.length) return <EmptyState compact title="No activity yet" />;

  return (
    <Box component="ol" sx={{ listStyle: 'none', p: 0, m: 0 }}>
      {events.map((event, index) => {
        const Icon = event.Icon;
        return (
          <Box component="li" key={event.id} sx={{ display: 'flex', gap: 2, position: 'relative', pb: index === events.length - 1 ? 0 : 3 }}>
            {index < events.length - 1 && <Box aria-hidden sx={{ position: 'absolute', left: 17, top: 38, bottom: 0, width: 2, bgcolor: 'divider' }} />}
            <Box
              sx={{
                width: 36,
                height: 36,
                flexShrink: 0,
                borderRadius: '50%',
                border: 2,
                borderColor: event.tone,
                color: event.tone,
                display: 'grid',
                placeItems: 'center',
                bgcolor: 'background.paper',
              }}
            >
              <Icon sx={{ fontSize: 18 }} />
            </Box>
            <Box sx={{ minWidth: 0 }}>
              <Typography variant="caption" sx={{ fontWeight: 600 }}>
                {formatDate(event.date)} · {formatRelativeTime(event.date)}
              </Typography>
              <Typography variant="body2" sx={{ fontWeight: 600 }}>
                {event.title}
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ wordBreak: 'break-word' }}>
                {event.detail}
              </Typography>
            </Box>
          </Box>
        );
      })}
    </Box>
  );
}
