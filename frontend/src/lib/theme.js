'use client';

import { createTheme } from '@mui/material/styles';

const navy = '#0f1e3c';
const border = '#e3e8ef';

const theme = createTheme({
  palette: {
    mode: 'light',
    primary: { main: '#1f5fd6', dark: '#174aa8', light: '#4f83e6', contrastText: '#ffffff' },
    secondary: { main: '#0f1e3c' },
    success: { main: '#1e8e5a', light: '#e6f5ee' },
    warning: { main: '#b7791f', light: '#fdf3e1' },
    error: { main: '#c8372d' },
    text: { primary: navy, secondary: '#52607a' },
    background: { default: '#f4f6fa', paper: '#ffffff' },
    divider: border,
  },
  shape: { borderRadius: 10 },
  typography: {
    fontFamily: '"Inter", "Segoe UI", system-ui, -apple-system, Roboto, "Helvetica Neue", Arial, sans-serif',
    h4: { fontWeight: 700, fontSize: '1.65rem', letterSpacing: '-0.01em' },
    h5: { fontWeight: 700, fontSize: '1.3rem' },
    h6: { fontWeight: 650, fontSize: '1.05rem' },
    subtitle1: { fontWeight: 600 },
    subtitle2: { fontWeight: 600, fontSize: '0.85rem' },
    body2: { fontSize: '0.875rem' },
    caption: { color: '#6b7891' },
    button: { textTransform: 'none', fontWeight: 600 },
    overline: { fontWeight: 700, letterSpacing: '0.08em', color: '#6b7891' },
  },
  components: {
    MuiCssBaseline: {
      styleOverrides: {
        body: { backgroundColor: '#f4f6fa' },
      },
    },
    MuiPaper: {
      defaultProps: { elevation: 0 },
      styleOverrides: {
        outlined: { borderColor: border },
      },
    },
    MuiCard: {
      defaultProps: { variant: 'outlined' },
      styleOverrides: {
        root: { borderColor: border, boxShadow: '0 1px 2px rgba(15, 30, 60, 0.04)' },
      },
    },
    MuiButton: {
      defaultProps: { disableElevation: true },
      styleOverrides: { root: { borderRadius: 8 } },
    },
    MuiChip: { styleOverrides: { root: { fontWeight: 500 } } },
    MuiTableCell: {
      styleOverrides: {
        root: { borderColor: border },
        head: { fontWeight: 600, color: '#52607a', fontSize: '0.78rem', textTransform: 'uppercase', letterSpacing: '0.04em', backgroundColor: '#f8fafc' },
      },
    },
    MuiTab: { styleOverrides: { root: { textTransform: 'none', fontWeight: 600, minHeight: 48 } } },
    MuiTooltip: { defaultProps: { arrow: true } },
    MuiCheckbox: { defaultProps: { size: 'small' } },
  },
});

export default theme;

/** Chart colours (reference data-viz palette, light mode). */
export const chartColors = {
  series1: '#2a78d6',
  series2: '#eb6834',
  bandFill: '#eb6834',
  grid: '#e8ecf2',
  axis: '#6b7891',
  text: '#0f1e3c',
};
