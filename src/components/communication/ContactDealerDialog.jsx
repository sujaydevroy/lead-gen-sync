'use client';

import Link from 'next/link';
import Dialog from '@mui/material/Dialog';
import DialogTitle from '@mui/material/DialogTitle';
import DialogContent from '@mui/material/DialogContent';
import IconButton from '@mui/material/IconButton';
import Box from '@mui/material/Box';
import Stack from '@mui/material/Stack';
import Grid from '@mui/material/Grid';
import Typography from '@mui/material/Typography';
import Button from '@mui/material/Button';
import Divider from '@mui/material/Divider';
import useMediaQuery from '@mui/material/useMediaQuery';
import { useTheme } from '@mui/material/styles';
import CloseRoundedIcon from '@mui/icons-material/CloseRounded';
import EmailOutlinedIcon from '@mui/icons-material/EmailOutlined';
import PhoneOutlinedIcon from '@mui/icons-material/PhoneOutlined';
import ContentCopyRoundedIcon from '@mui/icons-material/ContentCopyRounded';
import ChatBubbleOutlineRoundedIcon from '@mui/icons-material/ChatBubbleOutlineRounded';
import OpenInNewRoundedIcon from '@mui/icons-material/OpenInNewRounded';
import EntityAvatar from '@/components/ui/EntityAvatar';
import StatusBadge from '@/components/ui/StatusBadge';
import InfoGrid from '@/components/ui/InfoGrid';
import CountryLabel from '@/components/ui/CountryLabel';
import useDealerActions from '@/hooks/useDealerActions';
import useCommunications from '@/hooks/useCommunications';
import SendMessageForm from './SendMessageForm';
import CommunicationHistory from './CommunicationHistory';

/** Communication workspace for one dealer: details, quick actions, message form and history. */
export default function ContactDealerDialog({ dealer, open, onClose }) {
  const theme = useTheme();
  const fullScreen = useMediaQuery(theme.breakpoints.down('sm'));

  return (
    <Dialog open={open && Boolean(dealer)} onClose={onClose} fullWidth maxWidth="lg" fullScreen={fullScreen} aria-labelledby="contact-dealer-title">
      {dealer && <DialogBody dealer={dealer} onClose={onClose} />}
    </Dialog>
  );
}

function DialogBody({ dealer, onClose }) {
  const { sendEmail, call, copyEmail, copyPhone } = useDealerActions();
  const history = useCommunications({ dealerId: dealer.dealer_id });

  const focusMessage = () => document.getElementById('contact-message-form')?.querySelector('input:not([readonly]), textarea')?.focus();

  const actions = [
    { label: 'Send Email', Icon: EmailOutlinedIcon, onClick: () => sendEmail(dealer) },
    { label: 'Send Message', Icon: ChatBubbleOutlineRoundedIcon, onClick: focusMessage },
    { label: 'Call', Icon: PhoneOutlinedIcon, onClick: () => call(dealer) },
    { label: 'Copy Email', Icon: ContentCopyRoundedIcon, onClick: () => copyEmail(dealer) },
    { label: 'Copy Phone Number', Icon: ContentCopyRoundedIcon, onClick: () => copyPhone(dealer) },
  ];

  return (
    <>
      <DialogTitle id="contact-dealer-title" sx={{ pr: 7 }}>
        <Stack direction="row" spacing={1.5} sx={{ alignItems: 'center' }}>
          <EntityAvatar name={dealer.dealer_name} size={44} />
          <Box sx={{ minWidth: 0 }}>
            <Stack direction="row" spacing={1} sx={{ alignItems: 'center', flexWrap: 'wrap' }}>
              <Typography variant="h6" component="span">
                Contact {dealer.dealer_name}
              </Typography>
              <StatusBadge status={dealer.status} />
            </Stack>
            <Typography variant="body2" color="text.secondary">
              {dealer.company_name} · {dealer.dealer_id}
            </Typography>
          </Box>
        </Stack>
        <IconButton aria-label="Close" onClick={onClose} sx={{ position: 'absolute', right: 12, top: 12 }}>
          <CloseRoundedIcon />
        </IconButton>
      </DialogTitle>
      <Divider />
      <DialogContent sx={{ p: { xs: 2, sm: 3 } }}>
        <Grid container spacing={3}>
          <Grid size={{ xs: 12, md: 7 }}>
            <InfoGrid
              columns={3}
              items={[
                { label: 'Dealer name', value: dealer.dealer_name },
                { label: 'Company', value: dealer.company_name },
                { label: 'Country', value: <CountryLabel country={dealer.country} /> },
                { label: 'Region', value: `${dealer.region} · ${dealer.city}` },
                { label: 'Contact person', value: dealer.contact_person },
                { label: 'Phone', value: dealer.phone },
                { label: 'Email', value: dealer.email, full: true },
              ]}
            />

            <Typography variant="overline" component="h3" sx={{ display: 'block', mt: 3, mb: 1 }}>
              Communication options
            </Typography>
            <Stack direction="row" sx={{ flexWrap: 'wrap', gap: 1 }}>
              {actions.map(({ label, Icon, onClick }) => (
                <Button key={label} variant="outlined" size="small" startIcon={<Icon />} onClick={onClick}>
                  {label}
                </Button>
              ))}
            </Stack>

            <Typography variant="overline" component="h3" sx={{ display: 'block', mt: 3, mb: 1.5 }}>
              Send message
            </Typography>
            <Box id="contact-message-form">
              <SendMessageForm dealer={dealer} onCancel={onClose} />
            </Box>
          </Grid>

          <Grid size={{ xs: 12, md: 5 }}>
            <Box sx={{ bgcolor: '#f8fafc', border: 1, borderColor: 'divider', borderRadius: 2, p: 2, height: '100%' }}>
              <Stack direction="row" sx={{ alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
                <Typography variant="subtitle1" component="h3">
                  Communication History {history.data ? `(${history.data.length})` : ''}
                </Typography>
                <Button
                  size="small"
                  component={Link}
                  href={`/dealers/${dealer.dealer_id}?tab=communication`}
                  endIcon={<OpenInNewRoundedIcon sx={{ fontSize: '14px !important' }} />}
                  onClick={onClose}
                >
                  Full profile
                </Button>
              </Stack>
              {history.error ? (
                <Typography variant="body2" color="error">
                  Unable to load history. <Button size="small" onClick={history.reload}>Retry</Button>
                </Typography>
              ) : (
                <CommunicationHistory items={history.data} loading={history.loading} maxHeight={{ xs: 'none', md: 520 }} />
              )}
            </Box>
          </Grid>
        </Grid>
      </DialogContent>
    </>
  );
}
