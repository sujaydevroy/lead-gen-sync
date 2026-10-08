'use client';

import ToggleButton from '@mui/material/ToggleButton';
import ToggleButtonGroup from '@mui/material/ToggleButtonGroup';
import Tooltip from '@mui/material/Tooltip';
import { SCENARIOS } from '@/lib/salesForecast';

export default function ForecastScenarioSelector({ value, onChange, disabled }) {
  return (
    <ToggleButtonGroup
      size="small"
      exclusive
      value={value}
      onChange={(_, v) => v && onChange(v)}
      aria-label="Forecast scenario"
      disabled={disabled}
      sx={{ bgcolor: 'background.paper' }}
    >
      {Object.entries(SCENARIOS).map(([key, { label, description }]) => (
        <Tooltip key={key} title={description}>
          <ToggleButton value={key} sx={{ px: 1.75 }}>
            {label}
          </ToggleButton>
        </Tooltip>
      ))}
    </ToggleButtonGroup>
  );
}
