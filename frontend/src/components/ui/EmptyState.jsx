import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Button from '@mui/material/Button';
import SearchOffRoundedIcon from '@mui/icons-material/SearchOffRounded';
import ErrorOutlineRoundedIcon from '@mui/icons-material/ErrorOutlineRounded';

/** Generic empty / error state block with an optional action. */
export default function EmptyState({
  title,
  description,
  actionLabel,
  onAction,
  icon,
  variant = 'empty', // empty | error
  compact = false,
  children,
}) {
  const Icon = variant === 'error' ? ErrorOutlineRoundedIcon : SearchOffRoundedIcon;
  return (
    <Box
      role={variant === 'error' ? 'alert' : 'status'}
      sx={{
        textAlign: 'center',
        py: compact ? 4 : 8,
        px: 3,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        gap: 1,
      }}
    >
      <Box
        sx={{
          width: 56,
          height: 56,
          borderRadius: '50%',
          display: 'grid',
          placeItems: 'center',
          bgcolor: variant === 'error' ? 'rgba(200,55,45,0.08)' : 'rgba(31,95,214,0.08)',
          color: variant === 'error' ? 'error.main' : 'primary.main',
          mb: 1,
        }}
      >
        {icon || <Icon />}
      </Box>
      <Typography variant="h6">{title}</Typography>
      {description && (
        <Typography variant="body2" color="text.secondary" sx={{ maxWidth: 460 }}>
          {description}
        </Typography>
      )}
      {children}
      {actionLabel && onAction && (
        <Button variant={variant === 'error' ? 'contained' : 'outlined'} onClick={onAction} sx={{ mt: 1.5 }}>
          {actionLabel}
        </Button>
      )}
    </Box>
  );
}
