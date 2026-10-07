'use client';

import { useState } from 'react';
import Link from 'next/link';
import IconButton from '@mui/material/IconButton';
import Menu from '@mui/material/Menu';
import MenuItem from '@mui/material/MenuItem';
import ListItemIcon from '@mui/material/ListItemIcon';
import Divider from '@mui/material/Divider';
import Tooltip from '@mui/material/Tooltip';
import MoreVertRoundedIcon from '@mui/icons-material/MoreVertRounded';
import VisibilityOutlinedIcon from '@mui/icons-material/VisibilityOutlined';
import EmailOutlinedIcon from '@mui/icons-material/EmailOutlined';
import PhoneOutlinedIcon from '@mui/icons-material/PhoneOutlined';
import ContentCopyRoundedIcon from '@mui/icons-material/ContentCopyRounded';
import ChatBubbleOutlineRoundedIcon from '@mui/icons-material/ChatBubbleOutlineRounded';
import useDealerActions from '@/hooks/useDealerActions';

/** "More" (⋮) menu for a dealer row/card. */
export default function DealerActionsMenu({ dealer, onContact }) {
  const [anchor, setAnchor] = useState(null);
  const { sendEmail, call, copyEmail, copyPhone } = useDealerActions();

  const run = (fn) => () => {
    setAnchor(null);
    fn(dealer);
  };

  return (
    <>
      <Tooltip title="More actions">
        <IconButton
          size="small"
          aria-label={`More actions for ${dealer.dealer_name}`}
          aria-haspopup="menu"
          onClick={(e) => {
            e.stopPropagation();
            setAnchor(e.currentTarget);
          }}
        >
          <MoreVertRoundedIcon fontSize="small" />
        </IconButton>
      </Tooltip>
      <Menu
        anchorEl={anchor}
        open={Boolean(anchor)}
        onClose={() => setAnchor(null)}
        onClick={(e) => e.stopPropagation()}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
        transformOrigin={{ vertical: 'top', horizontal: 'right' }}
      >
        <MenuItem component={Link} href={`/dealers/${dealer.dealer_id}`} onClick={() => setAnchor(null)}>
          <ListItemIcon>
            <VisibilityOutlinedIcon fontSize="small" />
          </ListItemIcon>
          View dealer
        </MenuItem>
        <MenuItem onClick={run(onContact)}>
          <ListItemIcon>
            <ChatBubbleOutlineRoundedIcon fontSize="small" />
          </ListItemIcon>
          Send message
        </MenuItem>
        <MenuItem onClick={run(sendEmail)}>
          <ListItemIcon>
            <EmailOutlinedIcon fontSize="small" />
          </ListItemIcon>
          Send email
        </MenuItem>
        <MenuItem onClick={run(call)}>
          <ListItemIcon>
            <PhoneOutlinedIcon fontSize="small" />
          </ListItemIcon>
          Call
        </MenuItem>
        <Divider />
        <MenuItem onClick={run(copyEmail)}>
          <ListItemIcon>
            <ContentCopyRoundedIcon fontSize="small" />
          </ListItemIcon>
          Copy email
        </MenuItem>
        <MenuItem onClick={run(copyPhone)}>
          <ListItemIcon>
            <ContentCopyRoundedIcon fontSize="small" />
          </ListItemIcon>
          Copy phone number
        </MenuItem>
      </Menu>
    </>
  );
}
