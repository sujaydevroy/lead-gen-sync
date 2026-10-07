'use client';

import Table from '@mui/material/Table';
import TableHead from '@mui/material/TableHead';
import TableBody from '@mui/material/TableBody';
import TableRow from '@mui/material/TableRow';
import TableCell from '@mui/material/TableCell';
import Typography from '@mui/material/Typography';
import TrendingDownRoundedIcon from '@mui/icons-material/TrendingDownRounded';
import { formatCurrency, formatPercent, formatPeriodShort } from '@/lib/format';

/** Entities whose sales dropped between two equal windows at the end of the history. */
export default function DeclinersTable({ result, currency, nameLabel }) {
  if (!result.window) {
    return (
      <Typography variant="body2" color="text.secondary">
        At least 2 months of history are needed to compare periods.
      </Typography>
    );
  }
  const windowText = `${formatPeriodShort(result.priorRange[0])}–${formatPeriodShort(result.priorRange[1])} vs ${formatPeriodShort(result.recentRange[0])}–${formatPeriodShort(result.recentRange[1])}`;
  return (
    <>
      <Typography variant="caption" component="p" sx={{ mb: 1 }}>
        {windowText} ({result.window}-month windows)
      </Typography>
      {result.items.length === 0 ? (
        <Typography variant="body2" color="text.secondary">
          No {nameLabel.toLowerCase()}s declined between these periods.
        </Typography>
      ) : (
        <Table size="small" aria-label={`Declining ${nameLabel}s`}>
          <TableHead>
            <TableRow>
              <TableCell>{nameLabel}</TableCell>
              <TableCell align="right">Before</TableCell>
              <TableCell align="right">Recent</TableCell>
              <TableCell align="right">Change</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {result.items.slice(0, 6).map((item) => (
              <TableRow key={item.name}>
                <TableCell sx={{ maxWidth: 180, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} title={item.name}>
                  {item.name}
                </TableCell>
                <TableCell align="right" sx={{ whiteSpace: 'nowrap' }}>
                  {formatCurrency(item.prior, currency, { compact: true })}
                </TableCell>
                <TableCell align="right" sx={{ whiteSpace: 'nowrap' }}>
                  {formatCurrency(item.recent, currency, { compact: true })}
                </TableCell>
                <TableCell align="right" sx={{ whiteSpace: 'nowrap', color: 'error.main', fontWeight: 600 }}>
                  <TrendingDownRoundedIcon sx={{ fontSize: 14, verticalAlign: 'middle', mr: 0.25 }} />
                  {formatPercent(item.change)}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
    </>
  );
}
