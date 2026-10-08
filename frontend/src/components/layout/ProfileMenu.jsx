'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useDispatch } from 'react-redux';
import Box from '@mui/material/Box';
import ButtonBase from '@mui/material/ButtonBase';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';
import Menu from '@mui/material/Menu';
import MenuItem from '@mui/material/MenuItem';
import ListItemIcon from '@mui/material/ListItemIcon';
import Divider from '@mui/material/Divider';
import Chip from '@mui/material/Chip';
import Avatar from '@mui/material/Avatar';
import KeyboardArrowDownRoundedIcon from '@mui/icons-material/KeyboardArrowDownRounded';
import LogoutRoundedIcon from '@mui/icons-material/LogoutRounded';
import PlaceOutlinedIcon from '@mui/icons-material/PlaceOutlined';
import { useAuth } from '@/components/providers/AuthProvider';
import { useNotify } from '@/components/providers/NotificationProvider';
import EntityAvatar from '@/components/ui/EntityAvatar';
import { clearSalesData } from '@/store/salesSlice';
import { clearFilters } from '@/store/dealerListSlice';
import { initials } from '@/lib/format';
import { PROFILE_MENU_ITEMS } from './navConfig';

/** Company + user area in the header. Clicking it opens the account dropdown. */
export default function ProfileMenu() {
  const router = useRouter();
  const dispatch = useDispatch();
  const notify = useNotify();
  const { user, company, logout } = useAuth();
  const [anchor, setAnchor] = useState(null);
  const open = Boolean(anchor);

  const handleLogout = async () => {
    setAnchor(null);
    await logout();
    dispatch(clearSalesData());
    dispatch(clearFilters());
    notify('You have been signed out.', 'info');
    router.replace('/login');
  };

  if (!user) return null;

  return (
    <>
      <ButtonBase
        onClick={(e) => setAnchor(e.currentTarget)}
        aria-haspopup="menu"
        aria-expanded={open}
        aria-label="Open account menu"
        sx={{ borderRadius: 2, px: 1, py: 0.5, '&:hover': { bgcolor: 'action.hover' }, textAlign: 'left' }}
      >
        <Stack direction="row" spacing={1.5} sx={{ alignItems: 'center' }}>
          {company && (
            <Stack direction="row" spacing={1.25} sx={{ alignItems: 'center', display: { xs: 'none', lg: 'flex' } }}>
              <EntityAvatar name={company.name} text={company.logoText} size={34} />
              <Box sx={{ lineHeight: 1.2 }}>
                <Typography variant="subtitle2" sx={{ lineHeight: 1.25 }}>
                  {company.name}
                </Typography>
                <Typography variant="caption" sx={{ display: 'block', lineHeight: 1.25 }}>
                  ID {company.id} · {user.country}, {user.region}
                </Typography>
              </Box>
            </Stack>
          )}
          <Divider orientation="vertical" flexItem sx={{ display: { xs: 'none', lg: 'block' } }} />
          <Stack direction="row" spacing={1} sx={{ alignItems: 'center' }}>
            <Avatar sx={{ width: 34, height: 34, bgcolor: 'secondary.main', fontSize: 14, fontWeight: 700 }}>{initials(user.name)}</Avatar>
            <Box sx={{ display: { xs: 'none', sm: 'block' }, lineHeight: 1.2 }}>
              <Typography variant="subtitle2" sx={{ lineHeight: 1.25 }}>
                {user.name}
              </Typography>
              <Typography variant="caption" sx={{ display: 'block', lineHeight: 1.25 }}>
                {user.role}
              </Typography>
            </Box>
            <KeyboardArrowDownRoundedIcon fontSize="small" sx={{ color: 'text.secondary', transform: open ? 'rotate(180deg)' : 'none', transition: 'transform .2s' }} />
          </Stack>
        </Stack>
      </ButtonBase>

      <Menu
        anchorEl={anchor}
        open={open}
        onClose={() => setAnchor(null)}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
        transformOrigin={{ vertical: 'top', horizontal: 'right' }}
        slotProps={{ paper: { sx: { width: 320, mt: 1, border: 1, borderColor: 'divider', boxShadow: '0 12px 32px rgba(15,30,60,0.12)' } } }}
      >
        <Box sx={{ px: 2, pt: 1.5, pb: 2 }}>
          {company && (
            <Stack direction="row" spacing={1.5} sx={{ alignItems: 'center', mb: 2 }}>
              <EntityAvatar name={company.name} text={company.logoText} size={40} />
              <Box>
                <Typography variant="subtitle2">{company.name}</Typography>
                <Typography variant="caption">Company ID: {company.id}</Typography>
              </Box>
            </Stack>
          )}
          <Typography variant="subtitle2">{user.name}</Typography>
          <Typography variant="body2" color="text.secondary" sx={{ wordBreak: 'break-all' }}>
            {user.email}
          </Typography>
          <Stack direction="row" spacing={1} sx={{ mt: 1.25, flexWrap: 'wrap', rowGap: 1 }}>
            <Chip size="small" color="primary" variant="outlined" label={user.role} />
            <Chip size="small" variant="outlined" icon={<PlaceOutlinedIcon />} label={`${user.country} · ${user.region}`} />
          </Stack>
        </Box>
        <Divider />
        {PROFILE_MENU_ITEMS.map(({ label, href, Icon }) => (
          <MenuItem key={href} component={Link} href={href} onClick={() => setAnchor(null)} sx={{ py: 1.1 }}>
            <ListItemIcon>
              <Icon fontSize="small" />
            </ListItemIcon>
            {label}
          </MenuItem>
        ))}
        <Divider />
        <MenuItem onClick={handleLogout} sx={{ py: 1.1, color: 'error.main' }}>
          <ListItemIcon>
            <LogoutRoundedIcon fontSize="small" color="error" />
          </ListItemIcon>
          Logout
        </MenuItem>
      </Menu>
    </>
  );
}
