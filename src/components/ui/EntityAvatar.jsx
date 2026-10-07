import Avatar from '@mui/material/Avatar';
import { initials } from '@/lib/format';

const PALETTE = ['#1f5fd6', '#0f766e', '#7c3aed', '#b45309', '#be123c', '#0369a1', '#4d7c0f', '#334155'];

function colorFor(name = '') {
  let hash = 0;
  for (let i = 0; i < name.length; i += 1) hash = (hash * 31 + name.charCodeAt(i)) >>> 0;
  return PALETTE[hash % PALETTE.length];
}

/** Initials avatar used as a dealer / company logo placeholder. */
export default function EntityAvatar({ name, size = 40, variant = 'rounded', text }) {
  return (
    <Avatar
      variant={variant}
      sx={{
        width: size,
        height: size,
        bgcolor: colorFor(name),
        fontSize: size * 0.38,
        fontWeight: 700,
        borderRadius: variant === 'rounded' ? 2 : undefined,
      }}
      aria-hidden
    >
      {text || initials(name)}
    </Avatar>
  );
}
