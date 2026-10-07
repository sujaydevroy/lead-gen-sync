'use client';

import { useMemo } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import Box from '@mui/material/Box';
import Table from '@mui/material/Table';
import TableHead from '@mui/material/TableHead';
import TableBody from '@mui/material/TableBody';
import TableRow from '@mui/material/TableRow';
import TableCell from '@mui/material/TableCell';
import TableContainer from '@mui/material/TableContainer';
import TablePagination from '@mui/material/TablePagination';
import Typography from '@mui/material/Typography';
import DealerSearchField from '@/components/dealers/DealerSearchField';
import EmptyState from '@/components/ui/EmptyState';
import { setChartConfig } from '@/store/salesSlice';
import { formatCurrency, formatNumber, formatPeriod } from '@/lib/format';

const SEARCH_KEYS = ['customerName', 'country', 'location', 'product', 'currency', 'period'];

/** Searchable, paginated list of the converted sales records (search + paging kept in Redux). */
export default function SalesRecordsTable({ rows, reportingCurrency, converted }) {
  const dispatch = useDispatch();
  const { tableSearch, tablePage, tablePageSize } = useSelector((state) => state.sales.chartConfig);

  const matched = useMemo(() => {
    const term = tableSearch.trim().toLowerCase();
    if (!term) return rows;
    return rows.filter((r) => SEARCH_KEYS.some((k) => String(r[k] ?? '').toLowerCase().includes(term)));
  }, [rows, tableSearch]);

  const page = Math.min(tablePage, Math.max(0, Math.ceil(matched.length / tablePageSize) - 1));
  const pageRows = matched.slice(page * tablePageSize, page * tablePageSize + tablePageSize);

  return (
    <Box>
      <Box sx={{ p: 2 }}>
        <DealerSearchField
          value={tableSearch}
          onSearch={(v) => dispatch(setChartConfig({ tableSearch: v, tablePage: 0 }))}
          placeholder="Search by customer, product, country, location, currency or month..."
        />
        <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
          {matched.length} of {rows.length} records
        </Typography>
      </Box>
      {matched.length === 0 ? (
        <EmptyState compact title="No records match your search" actionLabel="Clear search" onAction={() => dispatch(setChartConfig({ tableSearch: '' }))} />
      ) : (
        <>
          <TableContainer>
            <Table size="small" sx={{ minWidth: 900 }} aria-label="Sales records">
              <TableHead>
                <TableRow>
                  <TableCell>Row</TableCell>
                  <TableCell>Customer</TableCell>
                  <TableCell>Country / Location</TableCell>
                  <TableCell>Month</TableCell>
                  <TableCell>Product</TableCell>
                  <TableCell align="right">Quantity</TableCell>
                  <TableCell align="right">Amount</TableCell>
                  {converted && <TableCell align="right">In {reportingCurrency}</TableCell>}
                </TableRow>
              </TableHead>
              <TableBody>
                {pageRows.map((r) => (
                  <TableRow key={r.id} hover>
                    <TableCell>{r.rowNumber}</TableCell>
                    <TableCell sx={{ fontWeight: 500 }}>{r.customerName}</TableCell>
                    <TableCell>
                      {r.country}
                      {r.location && (
                        <Typography variant="caption" component="div">
                          {r.location}
                        </Typography>
                      )}
                    </TableCell>
                    <TableCell sx={{ whiteSpace: 'nowrap' }}>{formatPeriod(r.period)}</TableCell>
                    <TableCell>{r.product}</TableCell>
                    <TableCell align="right" sx={{ whiteSpace: 'nowrap', fontVariantNumeric: 'tabular-nums' }}>
                      {r.quantity === null ? '—' : `${formatNumber(r.quantity)} ${r.unit}`}
                    </TableCell>
                    <TableCell align="right" sx={{ whiteSpace: 'nowrap', fontVariantNumeric: 'tabular-nums' }}>
                      {formatCurrency(r.amount, r.currency)}
                    </TableCell>
                    {converted && (
                      <TableCell align="right" sx={{ whiteSpace: 'nowrap', fontVariantNumeric: 'tabular-nums', color: 'text.secondary' }}>
                        {formatCurrency(r.value, reportingCurrency)}
                      </TableCell>
                    )}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
          <TablePagination
            component="div"
            count={matched.length}
            page={page}
            onPageChange={(_, p) => dispatch(setChartConfig({ tablePage: p }))}
            rowsPerPage={tablePageSize}
            onRowsPerPageChange={(e) => dispatch(setChartConfig({ tablePageSize: Number(e.target.value), tablePage: 0 }))}
            rowsPerPageOptions={[10, 20, 50]}
          />
        </>
      )}
    </Box>
  );
}
