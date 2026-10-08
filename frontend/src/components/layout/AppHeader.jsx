'use client';

import { useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import AppBar from '@mui/material/AppBar';
import Toolbar from '@mui/material/Toolbar';
import Box from '@mui/material/Box';
import IconButton from '@mui/material/IconButton';
import Tabs from '@mui/material/Tabs';
import Tab from '@mui/material/Tab';
import Drawer from '@mui/material/Drawer';
import List from '@mui/material/List';
import ListItemButton from '@mui/material/ListItemButton';
import ListItemIcon from '@mui/material/ListItemIcon';
import ListItemText from '@mui/material/ListItemText';
import Divider from '@mui/material/Divider';
import MenuRoundedIcon from '@mui/icons-material/MenuRounded';
import BrandMark from './BrandMark';
import ProfileMenu from './ProfileMenu';
import { NAV_ITEMS, activeNavHref } from './navConfig';

/** Top application header: brand, company/user dropdown and primary navigation. */
export default function AppHeader() {
  const pathname = usePathname();
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const active = activeNavHref(pathname);

  return (
    <AppBar position="sticky" color="inherit" elevation={0} sx={{ borderBottom: 1, borderColor: 'divider', bgcolor: 'background.paper' }}>
      <Toolbar sx={{ gap: 1.5, minHeight: { xs: 60, sm: 64 }, px: { xs: 1.5, sm: 3 } }}>
        <IconButton
          aria-label="Open navigation"
          onClick={() => setMobileNavOpen(true)}
          sx={{ display: { xs: 'inline-flex', md: 'none' } }}
        >
          <MenuRoundedIcon />
        </IconButton>
        <Box component={Link} href="/dealers" sx={{ textDecoration: 'none', color: 'inherit' }} aria-label="Go to dealers">
          <BrandMark />
        </Box>
        <Box sx={{ flexGrow: 1 }} />
        <ProfileMenu />
      </Toolbar>

      <Box sx={{ display: { xs: 'none', md: 'block' }, px: { md: 2, lg: 2.5 } }}>
        <Tabs
          value={active}
          variant="scrollable"
          scrollButtons="auto"
          aria-label="Main navigation"
          sx={{ minHeight: 44, '& .MuiTab-root': { minHeight: 44, py: 0, px: 1.75 } }}
        >
          {NAV_ITEMS.map(({ label, href, Icon }) => (
            <Tab key={href} value={href} label={label} icon={<Icon sx={{ fontSize: 18 }} />} iconPosition="start" component={Link} href={href} />
          ))}
        </Tabs>
      </Box>

      <Drawer open={mobileNavOpen} onClose={() => setMobileNavOpen(false)} slotProps={{ paper: { sx: { width: 280 } } }}>
        <Box sx={{ p: 2 }}>
          <BrandMark />
        </Box>
        <Divider />
        <List component="nav" aria-label="Main navigation" sx={{ px: 1 }}>
          {NAV_ITEMS.map(({ label, href, Icon }) => (
            <ListItemButton
              key={href}
              component={Link}
              href={href}
              selected={active === href}
              onClick={() => setMobileNavOpen(false)}
              sx={{ borderRadius: 2, mb: 0.5 }}
            >
              <ListItemIcon sx={{ minWidth: 38 }}>
                <Icon fontSize="small" />
              </ListItemIcon>
              <ListItemText primary={label} />
            </ListItemButton>
          ))}
        </List>
      </Drawer>
    </AppBar>
  );
}
