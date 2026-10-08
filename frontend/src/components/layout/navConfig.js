import DashboardRoundedIcon from '@mui/icons-material/DashboardRounded';
import StorefrontRoundedIcon from '@mui/icons-material/StorefrontRounded';
import ForumRoundedIcon from '@mui/icons-material/ForumRounded';
import UploadFileRoundedIcon from '@mui/icons-material/UploadFileRounded';
import InsightsRoundedIcon from '@mui/icons-material/InsightsRounded';
import BusinessRoundedIcon from '@mui/icons-material/BusinessRounded';
import PersonRoundedIcon from '@mui/icons-material/PersonRounded';
import SettingsRoundedIcon from '@mui/icons-material/SettingsRounded';

export const NAV_ITEMS = [
  { label: 'Dashboard', href: '/dashboard', Icon: DashboardRoundedIcon },
  { label: 'Dealers', href: '/dealers', Icon: StorefrontRoundedIcon },
  { label: 'Communications', href: '/communications', Icon: ForumRoundedIcon },
  { label: 'Upload Sales', href: '/sales', Icon: UploadFileRoundedIcon },
  { label: 'Sales Forecast', href: '/forecast', Icon: InsightsRoundedIcon },
  { label: 'Company Details', href: '/company', Icon: BusinessRoundedIcon },
  { label: 'My Profile', href: '/profile', Icon: PersonRoundedIcon },
  { label: 'Settings', href: '/settings', Icon: SettingsRoundedIcon },
];

/** Items in the header profile dropdown ("Upload Sales" sits before "Company Details"). */
export const PROFILE_MENU_ITEMS = ['/profile', '/sales', '/company', '/settings'].map((href) =>
  NAV_ITEMS.find((item) => item.href === href),
);

export function activeNavHref(pathname) {
  const match = NAV_ITEMS.filter((item) => pathname === item.href || pathname.startsWith(`${item.href}/`));
  return match.length ? match[match.length - 1].href : false;
}
