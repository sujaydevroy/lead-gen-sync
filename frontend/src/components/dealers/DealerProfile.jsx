'use client';

import { useMemo, useState } from 'react';
import Link from 'next/link';
import { usePathname, useRouter, useSearchParams } from 'next/navigation';
import Box from '@mui/material/Box';
import Card from '@mui/material/Card';
import Stack from '@mui/material/Stack';
import Grid from '@mui/material/Grid';
import Typography from '@mui/material/Typography';
import Button from '@mui/material/Button';
import Chip from '@mui/material/Chip';
import Tabs from '@mui/material/Tabs';
import Tab from '@mui/material/Tab';
import Breadcrumbs from '@mui/material/Breadcrumbs';
import MuiLink from '@mui/material/Link';
import Skeleton from '@mui/material/Skeleton';
import Tooltip from '@mui/material/Tooltip';
import IconButton from '@mui/material/IconButton';
import Alert from '@mui/material/Alert';
import ArrowBackRoundedIcon from '@mui/icons-material/ArrowBackRounded';
import ChatBubbleOutlineRoundedIcon from '@mui/icons-material/ChatBubbleOutlineRounded';
import EmailOutlinedIcon from '@mui/icons-material/EmailOutlined';
import PhoneOutlinedIcon from '@mui/icons-material/PhoneOutlined';
import ContentCopyRoundedIcon from '@mui/icons-material/ContentCopyRounded';
import LanguageRoundedIcon from '@mui/icons-material/LanguageRounded';
import EntityAvatar from '@/components/ui/EntityAvatar';
import StatusBadge from '@/components/ui/StatusBadge';
import SectionCard from '@/components/ui/SectionCard';
import InfoGrid from '@/components/ui/InfoGrid';
import CountryLabel from '@/components/ui/CountryLabel';
import EmptyState from '@/components/ui/EmptyState';
import CommunicationHistory from '@/components/communication/CommunicationHistory';
import SendMessageForm from '@/components/communication/SendMessageForm';
import ContactDealerDialog from '@/components/communication/ContactDealerDialog';
import DealerActivityTimeline from './DealerActivityTimeline';
import dealerService from '@/services/dealerService';
import useAsync from '@/hooks/useAsync';
import useCommunications from '@/hooks/useCommunications';
import useCompanySector from '@/hooks/useCompanySector';
import useDealerActions from '@/hooks/useDealerActions';
import { dealerSubSectors } from '@/lib/sectorMatching';
import { hasValue } from '@/types/dealer';
import { formatCurrency, formatDate } from '@/lib/format';

const TABS = [
  { value: 'overview', label: 'Overview' },
  { value: 'contact', label: 'Contact Information' },
  { value: 'communication', label: 'Communication' },
  { value: 'activity', label: 'Activity' },
];

export default function DealerProfile({ dealerId }) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const requestedTab = searchParams.get('tab');
  const tab = TABS.some((t) => t.value === requestedTab) ? requestedTab : 'overview';
  const [contactOpen, setContactOpen] = useState(false);

  const { data: dealer, loading, error, reload } = useAsync(() => dealerService.getDealerById(dealerId), [dealerId]);
  const history = useCommunications({ dealerId });
  const actions = useDealerActions();
  const companySector = useCompanySector();

  const matchedSubSectors = useMemo(
    () => (dealer && companySector ? dealerSubSectors(dealer, companySector.sub_sectors) : []),
    [dealer, companySector],
  );

  const setTab = (value) => {
    const params = new URLSearchParams(searchParams.toString());
    if (value === 'overview') params.delete('tab');
    else params.set('tab', value);
    const query = params.toString();
    router.replace(query ? `${pathname}?${query}` : pathname, { scroll: false });
  };

  if (error) {
    const notFound = error.status === 404;
    return (
      <Card>
        <EmptyState
          variant={notFound ? 'empty' : 'error'}
          title={notFound ? 'Dealer not found' : 'Unable to load dealer.'}
          description={notFound ? `No dealer exists with ID "${dealerId}".` : 'Please try again.'}
          actionLabel={notFound ? 'Back to Dealers' : 'Retry'}
          onAction={notFound ? () => router.push('/dealers') : reload}
        />
      </Card>
    );
  }

  if (loading && !dealer) return <ProfileSkeleton />;

  const lastAmount = Number(dealer.last_transaction_amount);
  const lastTransaction =
    hasValue(dealer.last_transaction_amount) && Number.isFinite(lastAmount) && hasValue(dealer.currency)
      ? `${formatCurrency(lastAmount, dealer.currency)} on ${formatDate(dealer.last_transaction_date)}`
      : 'Not Available';

  return (
    <>
      <Breadcrumbs sx={{ mb: 2 }}>
        <MuiLink component={Link} href="/dealers" underline="hover" color="inherit" sx={{ display: 'inline-flex', alignItems: 'center', gap: 0.5 }}>
          <ArrowBackRoundedIcon sx={{ fontSize: 16 }} /> Dealers
        </MuiLink>
        <Typography color="text.primary">{dealer.dealer_name}</Typography>
      </Breadcrumbs>

      <Card sx={{ mb: 3 }}>
        <Stack direction={{ xs: 'column', md: 'row' }} spacing={2.5} sx={{ p: { xs: 2.5, md: 3 }, alignItems: { md: 'center' }, justifyContent: 'space-between' }}>
          <Stack direction="row" spacing={2} sx={{ alignItems: 'center', minWidth: 0 }}>
            <EntityAvatar name={dealer.dealer_name} size={60} />
            <Box sx={{ minWidth: 0 }}>
              <Stack direction="row" spacing={1.25} sx={{ alignItems: 'center', flexWrap: 'wrap', rowGap: 0.5 }}>
                <Typography variant="h5" component="h1">
                  {dealer.dealer_name}
                </Typography>
                <StatusBadge status={dealer.status} />
                {dealer.is_demo && <Chip size="small" variant="outlined" label="Demo record" />}
              </Stack>
              <Typography color="text.secondary" sx={{ mt: 0.25 }}>
                {dealer.dealer_id} · {dealer.company_name} · {dealer.dealer_type}
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mt: 0.25 }}>
                <CountryLabel country={dealer.country} /> · {dealer.region} · {dealer.city}
              </Typography>
            </Box>
          </Stack>
          <Stack direction="row" spacing={1} sx={{ flexWrap: 'wrap', rowGap: 1 }}>
            <Button variant="contained" startIcon={<ChatBubbleOutlineRoundedIcon />} onClick={() => setContactOpen(true)}>
              Contact
            </Button>
            <Button variant="outlined" startIcon={<EmailOutlinedIcon />} onClick={() => actions.sendEmail(dealer)}>
              Email
            </Button>
            <Button variant="outlined" startIcon={<PhoneOutlinedIcon />} onClick={() => actions.call(dealer)}>
              Call
            </Button>
          </Stack>
        </Stack>
        <Tabs
          value={tab}
          onChange={(_, value) => setTab(value)}
          variant="scrollable"
          scrollButtons="auto"
          sx={{ px: { xs: 1, md: 2 }, borderTop: 1, borderColor: 'divider' }}
        >
          {TABS.map((t) => (
            <Tab
              key={t.value}
              value={t.value}
              label={t.value === 'communication' && history.data ? `${t.label} (${history.data.length})` : t.label}
            />
          ))}
        </Tabs>
      </Card>

      {tab === 'overview' && (
        <Grid container spacing={3}>
          <Grid size={{ xs: 12, lg: 7 }}>
            <SectionCard title="Dealer overview">
              <InfoGrid
                items={[
                  { label: 'Dealer name', value: dealer.dealer_name },
                  { label: 'Dealer ID', value: dealer.dealer_id },
                  { label: 'Company', value: dealer.company_name },
                  { label: 'Status', value: <StatusBadge status={dealer.status} /> },
                  { label: 'Dealer type', value: dealer.dealer_type },
                  { label: 'Registration no.', value: dealer.registration_no },
                  { label: 'Country', value: <CountryLabel country={dealer.country} /> },
                  { label: 'Region', value: dealer.region },
                  { label: 'City', value: dealer.city },
                  { label: 'State / Province', value: dealer.state },
                  { label: 'Address', value: dealer.full_address, full: true },
                ]}
              />
            </SectionCard>
          </Grid>
          <Grid size={{ xs: 12, lg: 5 }}>
            <Stack spacing={3}>
              <SectionCard title="Contact">
                <InfoGrid
                  columns={1}
                  items={[
                    { label: 'Contact person', value: dealer.contact_person },
                    { label: 'Email', value: dealer.email },
                    { label: 'Phone', value: dealer.phone },
                    { label: 'Website', value: dealer.website },
                  ]}
                />
              </SectionCard>
              <SectionCard title="Sector & products">
                <InfoGrid
                  columns={1}
                  items={[
                    {
                      label: 'Sector',
                      value: (
                        <Stack direction="row" spacing={1} sx={{ alignItems: 'center', flexWrap: 'wrap' }}>
                          <span>{dealer.sector}</span>
                          {companySector && dealer.sector !== companySector.sector && (
                            <Chip size="small" color="warning" variant="outlined" label="Outside your company sector" />
                          )}
                        </Stack>
                      ),
                    },
                    {
                      label: 'Products',
                      value: (
                        <Stack direction="row" sx={{ flexWrap: 'wrap', gap: 0.75 }}>
                          {(dealer.product || []).map((p) => (
                            <Chip key={p} size="small" label={p} />
                          ))}
                        </Stack>
                      ),
                    },
                    {
                      label: companySector ? `Matched sub-sectors (${companySector.sector})` : 'Matched sub-sectors',
                      value: matchedSubSectors.length ? (
                        <Stack direction="row" sx={{ flexWrap: 'wrap', gap: 0.75 }}>
                          {matchedSubSectors.map((s) => (
                            <Chip key={s} size="small" color="primary" variant="outlined" label={s} />
                          ))}
                        </Stack>
                      ) : (
                        'None'
                      ),
                    },
                    { label: 'Last transaction', value: lastTransaction },
                    { label: 'Verified on', value: formatDate(dealer.verification_date) },
                  ]}
                />
              </SectionCard>
            </Stack>
          </Grid>
        </Grid>
      )}

      {tab === 'contact' && (
        <SectionCard title="Contact information">
          <Stack spacing={2.5}>
            <ContactRow label="Contact person" value={dealer.contact_person} />
            <ContactRow
              label="Email"
              value={dealer.email}
              actions={[
                { title: 'Send email', Icon: EmailOutlinedIcon, onClick: () => actions.sendEmail(dealer) },
                { title: 'Copy email', Icon: ContentCopyRoundedIcon, onClick: () => actions.copyEmail(dealer) },
              ]}
            />
            <ContactRow
              label="Phone"
              value={dealer.phone}
              actions={[
                { title: 'Call', Icon: PhoneOutlinedIcon, onClick: () => actions.call(dealer) },
                { title: 'Copy phone number', Icon: ContentCopyRoundedIcon, onClick: () => actions.copyPhone(dealer) },
              ]}
            />
            <ContactRow
              label="Website"
              value={dealer.website}
              actions={
                hasValue(dealer.website)
                  ? [{ title: 'Open website', Icon: LanguageRoundedIcon, href: dealer.website }]
                  : []
              }
            />
            <ContactRow label="Address" value={dealer.full_address} />
            <ContactRow label="Postal code" value={dealer.postal_code} />
            {dealer.is_demo && (
              <Alert severity="info" variant="outlined">
                This is a demo dealer record. Its email domain ends in <code>.example</code> and the phone number is fictional.
              </Alert>
            )}
          </Stack>
        </SectionCard>
      )}

      {tab === 'communication' && (
        <Grid container spacing={3}>
          <Grid size={{ xs: 12, lg: 5 }}>
            <SectionCard title="Send message" subtitle={`To ${dealer.contact_person !== 'Not Available' ? dealer.contact_person : dealer.dealer_name}`}>
              <SendMessageForm dealer={dealer} />
            </SectionCard>
          </Grid>
          <Grid size={{ xs: 12, lg: 7 }}>
            <SectionCard title="Communication History" subtitle="Messages, emails, calls and meetings with this dealer">
              {history.error ? (
                <EmptyState variant="error" compact title="Unable to load history." actionLabel="Retry" onAction={history.reload} />
              ) : (
                <CommunicationHistory items={history.data} loading={history.loading} />
              )}
            </SectionCard>
          </Grid>
        </Grid>
      )}

      {tab === 'activity' && (
        <SectionCard title="Activity" subtitle="Timeline of interactions and record changes">
          <DealerActivityTimeline dealer={dealer} communications={history.data} loading={history.loading} />
        </SectionCard>
      )}

      <ContactDealerDialog dealer={dealer} open={contactOpen} onClose={() => setContactOpen(false)} />
    </>
  );
}

function ContactRow({ label, value, actions = [] }) {
  return (
    <Stack direction="row" spacing={2} sx={{ alignItems: 'center', justifyContent: 'space-between', borderBottom: 1, borderColor: 'divider', pb: 2 }}>
      <Box sx={{ minWidth: 0 }}>
        <Typography variant="caption" sx={{ textTransform: 'uppercase', letterSpacing: '0.05em', fontWeight: 600 }}>
          {label}
        </Typography>
        <Typography variant="body1" sx={{ fontWeight: 500, wordBreak: 'break-word' }}>
          {hasValue(value) ? value : 'Not Available'}
        </Typography>
      </Box>
      <Stack direction="row" spacing={0.5}>
        {actions.map(({ title, Icon, onClick, href }) => (
          <Tooltip key={title} title={title}>
            <IconButton
              aria-label={title}
              onClick={onClick}
              {...(href ? { component: 'a', href, target: '_blank', rel: 'noopener noreferrer' } : {})}
            >
              <Icon fontSize="small" />
            </IconButton>
          </Tooltip>
        ))}
      </Stack>
    </Stack>
  );
}

function ProfileSkeleton() {
  return (
    <Box aria-busy="true" aria-label="Loading dealer">
      <Skeleton width={180} height={28} sx={{ mb: 2 }} />
      <Card sx={{ p: 3, mb: 3 }}>
        <Stack direction="row" spacing={2} sx={{ alignItems: 'center' }}>
          <Skeleton variant="rounded" width={60} height={60} />
          <Box sx={{ flexGrow: 1 }}>
            <Skeleton width="40%" height={34} />
            <Skeleton width="55%" />
          </Box>
        </Stack>
      </Card>
      <Grid container spacing={3}>
        <Grid size={{ xs: 12, lg: 7 }}>
          <Skeleton variant="rounded" height={320} />
        </Grid>
        <Grid size={{ xs: 12, lg: 5 }}>
          <Skeleton variant="rounded" height={320} />
        </Grid>
      </Grid>
    </Box>
  );
}
