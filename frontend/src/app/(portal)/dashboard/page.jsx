'use client';

import { useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import Grid from '@mui/material/Grid';
import Stack from '@mui/material/Stack';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Button from '@mui/material/Button';
import List from '@mui/material/List';
import ListItemButton from '@mui/material/ListItemButton';
import ListItemAvatar from '@mui/material/ListItemAvatar';
import ListItemText from '@mui/material/ListItemText';
import ToggleButton from '@mui/material/ToggleButton';
import ToggleButtonGroup from '@mui/material/ToggleButtonGroup';
import Skeleton from '@mui/material/Skeleton';
import StorefrontRoundedIcon from '@mui/icons-material/StorefrontRounded';
import CheckCircleOutlineRoundedIcon from '@mui/icons-material/CheckCircleOutlineRounded';
import PublicRoundedIcon from '@mui/icons-material/PublicRounded';
import MapOutlinedIcon from '@mui/icons-material/MapOutlined';
import SendRoundedIcon from '@mui/icons-material/SendRounded';
import MarkEmailReadOutlinedIcon from '@mui/icons-material/MarkEmailReadOutlined';
import ArrowForwardRoundedIcon from '@mui/icons-material/ArrowForwardRounded';
import PageHeader from '@/components/ui/PageHeader';
import StatCard from '@/components/ui/StatCard';
import SectionCard from '@/components/ui/SectionCard';
import EmptyState from '@/components/ui/EmptyState';
import EntityAvatar from '@/components/ui/EntityAvatar';
import StatusBadge from '@/components/ui/StatusBadge';
import CountryLabel from '@/components/ui/CountryLabel';
import { TYPE_ICONS } from '@/components/communication/CommunicationHistory';
import { useAuth } from '@/components/providers/AuthProvider';
import dealerService from '@/services/dealerService';
import communicationService from '@/services/communicationService';
import useAsync from '@/hooks/useAsync';
import { formatDate, formatRelativeTime } from '@/lib/format';

export default function DashboardPage() {
  const { user } = useAuth();
  const [recentMode, setRecentMode] = useState('contacted');

  const dealerStats = useAsync(() => dealerService.getDealerStats(), []);
  const commStats = useAsync(() => communicationService.getCommunicationStats(), []);
  const recentComms = useAsync(() => communicationService.getRecentCommunications(30), []);
  const recentDealers = useAsync(() => dealerService.getRecentDealers(6), []);

  const reloadComms = commStats.reload;
  const reloadRecent = recentComms.reload;
  useEffect(
    () =>
      communicationService.subscribe(() => {
        reloadComms();
        reloadRecent();
      }),
    [reloadComms, reloadRecent],
  );

  // Latest outbound communication per dealer (up to 6), then load those dealers' details.
  const lastContacts = useMemo(() => {
    const seen = new Set();
    return (recentComms.data || [])
      .filter((c) => c.direction === 'outbound' && !seen.has(c.dealerId) && seen.add(c.dealerId))
      .slice(0, 6);
  }, [recentComms.data]);
  const contactedIds = lastContacts.map((c) => c.dealerId).join(',');
  const contactedDealers = useAsync(
    () => (contactedIds ? Promise.all(contactedIds.split(',').map((id) => dealerService.getDealerById(id))) : Promise.resolve([])),
    [contactedIds],
  );
  const recentlyContacted = useMemo(() => {
    const byId = new Map((contactedDealers.data || []).map((d) => [d.dealer_id, d]));
    return lastContacts
      .map((c) => ({ dealer: byId.get(c.dealerId), at: c.createdAt, subject: c.subject }))
      .filter((r) => r.dealer);
  }, [lastContacts, contactedDealers.data]);

  const hasError = dealerStats.error || commStats.error;
  const retryAll = () => {
    dealerStats.reload();
    commStats.reload();
    recentComms.reload();
    recentDealers.reload();
  };

  const stats = [
    { label: 'Total Dealers', value: dealerStats.data?.totalDealers, Icon: StorefrontRoundedIcon, loading: dealerStats.loading },
    { label: 'Active Dealers', value: dealerStats.data?.activeDealers, Icon: CheckCircleOutlineRoundedIcon, loading: dealerStats.loading },
    { label: 'Countries', value: dealerStats.data?.countries, Icon: PublicRoundedIcon, loading: dealerStats.loading },
    { label: 'Regions', value: dealerStats.data?.regions, Icon: MapOutlinedIcon, loading: dealerStats.loading, caption: 'Country–region combinations' },
    { label: 'Messages Sent', value: commStats.data?.sent, Icon: SendRoundedIcon, loading: commStats.loading && !commStats.data, caption: 'Emails & messages' },
    { label: 'Messages Received', value: commStats.data?.received, Icon: MarkEmailReadOutlinedIcon, loading: commStats.loading && !commStats.data, caption: 'Emails & messages' },
  ];

  return (
    <>
      <PageHeader
        title={`Welcome back, ${user.name.split(' ')[0]}`}
        subtitle="Overview of your dealer network and recent communication"
        actions={
          <Button component={Link} href="/dealers" variant="contained" endIcon={<ArrowForwardRoundedIcon />}>
            Find dealers
          </Button>
        }
      />

      {hasError ? (
        <SectionCard>
          <EmptyState variant="error" title="Unable to load the dashboard." description="Please try again." actionLabel="Retry" onAction={retryAll} />
        </SectionCard>
      ) : (
        <>
          <Grid container spacing={2} sx={{ mb: 3 }}>
            {stats.map(({ label, value, Icon, loading, caption }) => (
              <Grid key={label} size={{ xs: 6, sm: 4, lg: 2 }}>
                <StatCard label={label} value={value ?? '—'} icon={<Icon fontSize="small" />} loading={loading} caption={caption} />
              </Grid>
            ))}
          </Grid>

          <Grid container spacing={3}>
            <Grid size={{ xs: 12, lg: 6 }}>
              <SectionCard
                title="Recent Dealers"
                actions={
                  <ToggleButtonGroup size="small" exclusive value={recentMode} onChange={(_, v) => v && setRecentMode(v)} aria-label="Recent dealers view">
                    <ToggleButton value="contacted">Recently contacted</ToggleButton>
                    <ToggleButton value="added">Recently added</ToggleButton>
                  </ToggleButtonGroup>
                }
                noPadding
              >
                {recentMode === 'contacted' ? (
                  <DealerList
                    loading={(recentComms.loading && !recentComms.data) || (contactedDealers.loading && !contactedDealers.data)}
                    rows={recentlyContacted.map(({ dealer, at, subject }) => ({ dealer, secondary: `${subject} · ${formatRelativeTime(at)}` }))}
                    empty="No dealers contacted yet."
                  />
                ) : (
                  <DealerList
                    loading={recentDealers.loading}
                    rows={(recentDealers.data || []).map((dealer) => ({ dealer, secondary: `Added ${formatDate(dealer.created_at)}` }))}
                    empty="No dealers yet."
                  />
                )}
              </SectionCard>
            </Grid>
            <Grid size={{ xs: 12, lg: 6 }}>
              <SectionCard
                title="Recent Communications"
                actions={
                  <Button component={Link} href="/communications" size="small" endIcon={<ArrowForwardRoundedIcon />}>
                    View all
                  </Button>
                }
                noPadding
              >
                {recentComms.loading && !recentComms.data ? (
                  <Box sx={{ p: 2 }}>
                    {[0, 1, 2, 3].map((i) => (
                      <Skeleton key={i} height={52} />
                    ))}
                  </Box>
                ) : (
                  <List disablePadding>
                    {(recentComms.data || []).slice(0, 6).map((c) => {
                      const Icon = TYPE_ICONS[c.type];
                      return (
                        <ListItemButton key={c.id} component={Link} href={`/dealers/${c.dealerId}?tab=communication`} divider>
                          <ListItemAvatar>
                            <Box sx={{ width: 36, height: 36, borderRadius: 2, display: 'grid', placeItems: 'center', bgcolor: 'rgba(31,95,214,0.08)', color: 'primary.main' }}>
                              <Icon fontSize="small" />
                            </Box>
                          </ListItemAvatar>
                          <ListItemText
                            primary={c.dealerName || c.dealerId}
                            secondary={c.subject}
                            slotProps={{ primary: { variant: 'subtitle2' }, secondary: { noWrap: true } }}
                          />
                          <Stack sx={{ alignItems: 'flex-end', ml: 2, flexShrink: 0 }}>
                            <Typography variant="caption">{formatRelativeTime(c.createdAt)}</Typography>
                            <Typography variant="caption" sx={{ color: c.direction === 'inbound' ? 'primary.main' : 'success.main', fontWeight: 600 }}>
                              {c.direction === 'inbound' ? 'Received' : 'Sent'} · {c.type}
                            </Typography>
                          </Stack>
                        </ListItemButton>
                      );
                    })}
                  </List>
                )}
              </SectionCard>
            </Grid>
          </Grid>
        </>
      )}
    </>
  );
}

function DealerList({ rows, loading, empty }) {
  if (loading) {
    return (
      <Box sx={{ p: 2 }}>
        {[0, 1, 2, 3].map((i) => (
          <Skeleton key={i} height={56} />
        ))}
      </Box>
    );
  }
  if (!rows.length) return <EmptyState compact title={empty} />;
  return (
    <List disablePadding>
      {rows.map(({ dealer, secondary }) => (
        <ListItemButton key={dealer.dealer_id} component={Link} href={`/dealers/${dealer.dealer_id}`} divider>
          <ListItemAvatar>
            <EntityAvatar name={dealer.dealer_name} size={36} />
          </ListItemAvatar>
          <ListItemText
            primary={dealer.dealer_name}
            secondary={
              <>
                <CountryLabel country={dealer.country} /> · {dealer.region} — {secondary}
              </>
            }
            slotProps={{ primary: { variant: 'subtitle2' }, secondary: { noWrap: true } }}
          />
          <Box sx={{ ml: 2, flexShrink: 0 }}>
            <StatusBadge status={dealer.status} />
          </Box>
        </ListItemButton>
      ))}
    </List>
  );
}
