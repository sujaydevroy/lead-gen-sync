'use client';

import Link from 'next/link';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import CardActions from '@mui/material/CardActions';
import Box from '@mui/material/Box';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';
import Button from '@mui/material/Button';
import Divider from '@mui/material/Divider';
import Skeleton from '@mui/material/Skeleton';
import EntityAvatar from '@/components/ui/EntityAvatar';
import StatusBadge from '@/components/ui/StatusBadge';
import CountryLabel from '@/components/ui/CountryLabel';
import { displayValue } from '@/lib/format';
import DealerActionsMenu from './DealerActionsMenu';

const ellipsis = { overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' };

export function DealerCardSkeleton() {
  return (
    <Card>
      <CardContent>
        <Stack direction="row" spacing={1.5}>
          <Skeleton variant="rounded" width={44} height={44} />
          <Box sx={{ flexGrow: 1 }}>
            <Skeleton width="70%" />
            <Skeleton width="40%" />
          </Box>
        </Stack>
        <Skeleton sx={{ mt: 2 }} width="50%" />
        <Skeleton width="60%" />
        <Skeleton sx={{ mt: 1.5 }} width="45%" />
        <Skeleton width="75%" />
      </CardContent>
    </Card>
  );
}

export default function DealerCard({ dealer, onContact }) {
  const href = `/dealers/${dealer.dealer_id}`;
  return (
    <Card sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <CardContent sx={{ flexGrow: 1, pb: 1.5 }}>
        <Stack direction="row" spacing={1.5} sx={{ alignItems: 'flex-start' }}>
          <EntityAvatar name={dealer.dealer_name} size={44} />
          <Box sx={{ minWidth: 0, flexGrow: 1 }}>
            <Typography
              component={Link}
              href={href}
              variant="subtitle1"
              sx={{ ...ellipsis, display: 'block', color: 'text.primary', textDecoration: 'none', lineHeight: 1.3 }}
            >
              {dealer.dealer_name}
            </Typography>
            <Typography variant="caption">Dealer ID: {dealer.dealer_id}</Typography>
          </Box>
          <StatusBadge status={dealer.status} />
        </Stack>

        <Typography variant="body2" color="text.secondary" sx={{ mt: 1.5, ...ellipsis }}>
          {dealer.company_name} · {dealer.dealer_type}
        </Typography>

        <Box sx={{ mt: 1.5 }}>
          <Typography variant="body2" sx={{ fontWeight: 500 }}>
            <CountryLabel country={dealer.country} />
          </Typography>
          <Typography variant="body2" color="text.secondary">
            {dealer.region} • {dealer.city}
          </Typography>
        </Box>

        <Box sx={{ mt: 1.5 }}>
          <Typography variant="body2" sx={{ fontWeight: 500 }}>
            {displayValue(dealer.contact_person)}
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={ellipsis}>
            {displayValue(dealer.email)}
          </Typography>
          <Typography variant="body2" color="text.secondary">
            {displayValue(dealer.phone)}
          </Typography>
        </Box>
      </CardContent>
      <Divider />
      <CardActions sx={{ px: 2, py: 1.25, gap: 1 }}>
        <Button component={Link} href={href} size="small" variant="outlined" sx={{ flexGrow: 1 }}>
          View Dealer
        </Button>
        <Button size="small" variant="contained" onClick={() => onContact(dealer)} sx={{ flexGrow: 1, ml: '0 !important' }}>
          Contact
        </Button>
        <DealerActionsMenu dealer={dealer} onContact={onContact} />
      </CardActions>
    </Card>
  );
}
