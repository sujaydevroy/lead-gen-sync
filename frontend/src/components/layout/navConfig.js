import DashboardRoundedIcon from '@mui/icons-material/DashboardRounded';
import StorefrontRoundedIcon from '@mui/icons-material/StorefrontRounded';
import ForumRoundedIcon from '@mui/icons-material/ForumRounded';
import UploadFileRoundedIcon from '@mui/icons-material/UploadFileRounded';
import InsightsRoundedIcon from '@mui/icons-material/InsightsRounded';
import BusinessRoundedIcon from '@mui/icons-material/BusinessRounded';
import GroupRoundedIcon from '@mui/icons-material/GroupRounded';
import PersonRoundedIcon from '@mui/icons-material/PersonRounded';
import SettingsRoundedIcon from '@mui/icons-material/SettingsRounded';
import DomainAddRoundedIcon from '@mui/icons-material/DomainAddRounded';
import DriveFolderUploadRoundedIcon from '@mui/icons-material/DriveFolderUploadRounded';
import { canOpenPath } from '@/lib/roles';

export const NAV_ITEMS = [
  { label: 'Companies', href: '/admin/companies', Icon: DomainAddRoundedIcon },
  { label: 'Dealer Upload', href: '/admin/dealer-uploads', Icon: DriveFolderUploadRoundedIcon },
  { label: 'Dashboard', href: '/dashboard', Icon: DashboardRoundedIcon },
  { label: 'Dealers', href: '/dealers', Icon: StorefrontRoundedIcon },
  { label: 'Communications', href: '/communications', Icon: ForumRoundedIcon },
  { label: 'Upload Sales', href: '/sales', Icon: UploadFileRoundedIcon },
  { label: 'Sales Forecast', href: '/forecast', Icon: InsightsRoundedIcon },
  { label: 'Company Details', href: '/company', Icon: BusinessRoundedIcon },
  { label: 'Users', href: '/users', Icon: GroupRoundedIcon },
  { label: 'My Profile', href: '/profile', Icon: PersonRoundedIcon },
  { label: 'Settings', href: '/settings', Icon: SettingsRoundedIcon },
];

/** The navigation entries the user's role can open. */
export function navItemsFor(user) {
  return NAV_ITEMS.filter((item) => canOpenPath(user, item.href));
}

/** Items in the header profile dropdown ("Upload Sales" sits before "Company Details"). */
const PROFILE_MENU_HREFS = ['/profile', '/sales', '/company', '/users', '/settings'];

export function profileMenuItemsFor(user) {
  return PROFILE_MENU_HREFS.map((href) => NAV_ITEMS.find((item) => item.href === href)).filter((item) =>
    canOpenPath(user, item.href),
  );
}

export function activeNavHref(pathname) {
  const match = NAV_ITEMS.filter((item) => pathname === item.href || pathname.startsWith(`${item.href}/`));
  return match.length ? match[match.length - 1].href : false;
}
