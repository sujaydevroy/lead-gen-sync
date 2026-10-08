'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import Table from '@mui/material/Table';
import TableHead from '@mui/material/TableHead';
import TableBody from '@mui/material/TableBody';
import TableRow from '@mui/material/TableRow';
import TableCell from '@mui/material/TableCell';
import TableContainer from '@mui/material/TableContainer';
import Box from '@mui/material/Box';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';
import Button from '@mui/material/Button';
import IconButton from '@mui/material/IconButton';
import Tooltip from '@mui/material/Tooltip';
import Skeleton from '@mui/material/Skeleton';
import VisibilityOutlinedIcon from '@mui/icons-material/VisibilityOutlined';
import ChatBubbleOutlineRoundedIcon from '@mui/icons-material/ChatBubbleOutlineRounded';
import EntityAvatar from '@/components/ui/EntityAvatar';
import StatusBadge from '@/components/ui/StatusBadge';
import CountryLabel from '@/components/ui/CountryLabel';
import { displayValue } from '@/lib/format';
import DealerActionsMenu from './DealerActionsMenu';

// Column visibility by breakpoint: Company from xl, Location from lg; below that the
// information is folded into the Dealer cell so nothing is lost on narrower screens.
const onlyXl = { display: { xs: 'none', xl: 'table-cell' } };
const onlyLg = { display: { xs: 'none', lg: 'table-cell' } };

const ellipsis = { overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' };

export function DealerTableSkeleton({ rows = 8 }) {
  return (
    <TableContainer>
      <Table aria-label="Loading dealers">
        <TableBody>
          {Array.from({ length: rows }).map((_, i) => (
            <TableRow key={i}>
              <TableCell>
                <Stack direction="row" spacing={1.5} sx={{ alignItems: 'center' }}>
                  <Skeleton variant="rounded" width={40} height={40} />
                  <Box sx={{ flexGrow: 1 }}>
                    <Skeleton width="60%" />
                    <Skeleton width="35%" />
                  </Box>
                </Stack>
              </TableCell>
              <TableCell sx={onlyLg}>
                <Skeleton width="70%" />
                <Skeleton width="50%" />
              </TableCell>
              <TableCell>
                <Skeleton width="70%" />
                <Skeleton width="80%" />
              </TableCell>
              <TableCell width={110}>
                <Skeleton variant="rounded" width={72} height={24} />
              </TableCell>
              <TableCell width={170}>
                <Skeleton width="80%" />
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  );
}

export default function DealerTable({ dealers, onContact }) {
  const router = useRouter();

  return (
    <TableContainer>
      <Table aria-label="Dealers" sx={{ tableLayout: 'fixed' }}>
        <TableHead>
          <TableRow>
            <TableCell sx={{ width: { md: '38%', lg: '30%', xl: '24%' } }}>Dealer</TableCell>
            <TableCell sx={{ ...onlyXl, width: '18%' }}>Company</TableCell>
            <TableCell sx={{ ...onlyLg, width: { lg: '19%', xl: '16%' } }}>Location</TableCell>
            <TableCell>Contact</TableCell>
            <TableCell sx={{ width: 112 }}>Status</TableCell>
            <TableCell sx={{ width: 176 }} align="right">
              Actions
            </TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {dealers.map((dealer) => {
            const href = `/dealers/${dealer.dealer_id}`;
            return (
              <TableRow
                key={dealer.dealer_id}
                hover
                onClick={() => router.push(href)}
                sx={{ cursor: 'pointer', '&:last-child td': { borderBottom: 0 } }}
              >
                <TableCell>
                  <Stack direction="row" spacing={1.5} sx={{ alignItems: 'center', minWidth: 0 }}>
                    <EntityAvatar name={dealer.dealer_name} />
                    <Box sx={{ minWidth: 0 }}>
                      <Typography
                        component={Link}
                        href={href}
                        onClick={(e) => e.stopPropagation()}
                        variant="subtitle2"
                        sx={{ ...ellipsis, display: 'block', color: 'text.primary', textDecoration: 'none', '&:hover': { color: 'primary.main' } }}
                      >
                        {dealer.dealer_name}
                      </Typography>
                      <Typography variant="caption" component="div" sx={ellipsis}>
                        {dealer.dealer_id}
                      </Typography>
                      <Typography variant="caption" component="div" sx={{ ...ellipsis, display: { xs: 'block', xl: 'none' } }}>
                        {dealer.company_name} · {dealer.dealer_type}
                      </Typography>
                      <Typography variant="caption" component="div" sx={{ ...ellipsis, display: { xs: 'block', lg: 'none' } }}>
                        <CountryLabel country={dealer.country} /> · {dealer.region} · {dealer.city}
                      </Typography>
                    </Box>
                  </Stack>
                </TableCell>
                <TableCell sx={onlyXl}>
                  <Typography variant="body2" sx={{ ...ellipsis, fontWeight: 500 }}>
                    {dealer.company_name}
                  </Typography>
                  <Typography variant="caption" component="div">
                    {dealer.dealer_type}
                  </Typography>
                </TableCell>
                <TableCell sx={onlyLg}>
                  <Typography variant="body2" sx={ellipsis}>
                    <CountryLabel country={dealer.country} />
                  </Typography>
                  <Typography variant="caption" component="div" sx={ellipsis}>
                    {dealer.region} · {dealer.city}
                  </Typography>
                </TableCell>
                <TableCell>
                  <Typography variant="body2" sx={{ ...ellipsis, fontWeight: 500 }}>
                    {displayValue(dealer.contact_person)}
                  </Typography>
                  <Typography variant="caption" component="div" sx={ellipsis} title={dealer.email}>
                    {displayValue(dealer.email)}
                  </Typography>
                  <Typography variant="caption" component="div" sx={ellipsis}>
                    {displayValue(dealer.phone)}
                  </Typography>
                </TableCell>
                <TableCell>
                  <StatusBadge status={dealer.status} />
                </TableCell>
                <TableCell align="right" onClick={(e) => e.stopPropagation()}>
                  <Stack direction="row" spacing={0.5} sx={{ justifyContent: 'flex-end', alignItems: 'center' }}>
                    <Tooltip title="View dealer">
                      <IconButton size="small" component={Link} href={href} aria-label={`View ${dealer.dealer_name}`}>
                        <VisibilityOutlinedIcon fontSize="small" />
                      </IconButton>
                    </Tooltip>
                    <Button
                      size="small"
                      variant="outlined"
                      startIcon={<ChatBubbleOutlineRoundedIcon sx={{ fontSize: '16px !important' }} />}
                      onClick={() => onContact(dealer)}
                    >
                      Contact
                    </Button>
                    <DealerActionsMenu dealer={dealer} onContact={onContact} />
                  </Stack>
                </TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
    </TableContainer>
  );
}
