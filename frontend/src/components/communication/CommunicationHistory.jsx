'use client';

import Link from 'next/link';
import Box from '@mui/material/Box';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';
import Chip from '@mui/material/Chip';
import Skeleton from '@mui/material/Skeleton';
import Tooltip from '@mui/material/Tooltip';
import EmailOutlinedIcon from '@mui/icons-material/EmailOutlined';
import ChatBubbleOutlineRoundedIcon from '@mui/icons-material/ChatBubbleOutlineRounded';
import PhoneOutlinedIcon from '@mui/icons-material/PhoneOutlined';
import EventOutlinedIcon from '@mui/icons-material/EventOutlined';
import AttachFileRoundedIcon from '@mui/icons-material/AttachFileRounded';
import CallReceivedRoundedIcon from '@mui/icons-material/CallReceivedRounded';
import CallMadeRoundedIcon from '@mui/icons-material/CallMadeRounded';
import EmptyState from '@/components/ui/EmptyState';
import { formatDate, formatFileSize, formatRelativeTime } from '@/lib/format';

export const TYPE_ICONS = {
  Email: EmailOutlinedIcon,
  Message: ChatBubbleOutlineRoundedIcon,
  Call: PhoneOutlinedIcon,
  Meeting: EventOutlinedIcon,
};

const TYPE_VERBS = { Email: 'Email', Message: 'Message', Call: 'Call', Meeting: 'Meeting' };

export function describeCommunication(item) {
  const noun = TYPE_VERBS[item.type] || item.type;
  if (item.direction === 'inbound') return `${noun} received from dealer`;
  if (item.type === 'Meeting') return `Meeting held by ${item.sender}`;
  if (item.type === 'Call') return `Call by ${item.sender}`;
  return `${noun} sent by ${item.sender}`;
}

function StatusChip({ status }) {
  const color = status === 'Received' ? 'primary' : status === 'Initiated' ? 'warning' : 'success';
  return <Chip size="small" label={status} color={color} variant="outlined" sx={{ height: 22, fontSize: '0.72rem' }} />;
}

/**
 * Timeline of communications.
 * @param {{ items?: import('@/types/communication').Communication[], loading?: boolean,
 *           showDealer?: boolean, emptyText?: string, maxHeight?: number|string }} props
 */
export default function CommunicationHistory({ items, loading, showDealer = false, emptyText = 'No communication yet.', maxHeight }) {
  if (loading && !items) {
    return (
      <Stack spacing={2}>
        {[0, 1, 2].map((i) => (
          <Stack key={i} direction="row" spacing={1.5}>
            <Skeleton variant="circular" width={32} height={32} />
            <Box sx={{ flexGrow: 1 }}>
              <Skeleton width="40%" />
              <Skeleton width="70%" />
              <Skeleton width="55%" />
            </Box>
          </Stack>
        ))}
      </Stack>
    );
  }

  if (!items?.length) {
    return <EmptyState compact title="No communication history" description={emptyText} />;
  }

  return (
    <Box component="ol" sx={{ listStyle: 'none', p: 0, m: 0, maxHeight, overflowY: maxHeight ? 'auto' : 'visible', pr: maxHeight ? 1 : 0 }}>
      {items.map((item, index) => {
        const Icon = TYPE_ICONS[item.type] || ChatBubbleOutlineRoundedIcon;
        const inbound = item.direction === 'inbound';
        return (
          <Box component="li" key={item.id} sx={{ display: 'flex', gap: 1.5, position: 'relative', pb: index === items.length - 1 ? 0 : 2.5 }}>
            {index < items.length - 1 && (
              <Box aria-hidden sx={{ position: 'absolute', left: 15, top: 34, bottom: 0, width: 2, bgcolor: 'divider' }} />
            )}
            <Box
              sx={{
                width: 32,
                height: 32,
                flexShrink: 0,
                borderRadius: '50%',
                display: 'grid',
                placeItems: 'center',
                bgcolor: inbound ? 'rgba(31,95,214,0.1)' : 'rgba(30,142,90,0.1)',
                color: inbound ? 'primary.main' : 'success.main',
              }}
            >
              <Icon sx={{ fontSize: 17 }} />
            </Box>
            <Box sx={{ minWidth: 0, flexGrow: 1 }}>
              <Stack direction="row" spacing={1} sx={{ alignItems: 'center', flexWrap: 'wrap', rowGap: 0.5 }}>
                <Tooltip title={formatDate(item.createdAt, { withTime: true })}>
                  <Typography variant="caption" sx={{ fontWeight: 600 }}>
                    {formatDate(item.createdAt)} · {formatRelativeTime(item.createdAt)}
                  </Typography>
                </Tooltip>
                <Chip
                  size="small"
                  icon={inbound ? <CallReceivedRoundedIcon /> : <CallMadeRoundedIcon />}
                  label={item.type}
                  sx={{ height: 22, fontSize: '0.72rem' }}
                />
                <StatusChip status={item.status} />
              </Stack>
              <Typography variant="body2" sx={{ mt: 0.5, fontWeight: 600 }}>
                {describeCommunication(item)}
              </Typography>
              {showDealer && (
                <Typography variant="body2">
                  Dealer:{' '}
                  <Box component={Link} href={`/dealers/${item.dealerId}`} sx={{ color: 'primary.main', textDecoration: 'none' }}>
                    {item.dealerName || item.dealerId}
                  </Box>
                </Typography>
              )}
              <Typography variant="body2" color="text.secondary">
                Subject: {item.subject}
              </Typography>
              <Typography variant="caption" component="div">
                From {item.sender} → To {item.recipient}
              </Typography>
              {item.body && (
                <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5, whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
                  {item.body}
                </Typography>
              )}
              {item.attachments?.map((a) => (
                <Chip
                  key={a.id ?? a.name}
                  size="small"
                  variant="outlined"
                  icon={<AttachFileRoundedIcon />}
                  label={`${a.name} (${formatFileSize(a.size)})`}
                  title={a.url ? `Download ${a.name}` : undefined}
                  {...(a.url ? { component: 'a', href: a.url, download: a.name, clickable: true } : {})}
                  sx={{ mt: 0.75, maxWidth: '100%' }}
                />
              ))}
            </Box>
          </Box>
        );
      })}
    </Box>
  );
}
