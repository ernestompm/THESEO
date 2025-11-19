import React, { useState } from 'react';
import { Select, MenuItem, Paper, FormControl, InputLabel, Box } from '@mui/material';

// Mock data, to be replaced by backend data.
const mockFlagsByEvent = {
  'SWMW100MFR----------': [
    { noc: 'SWE', flag_url_cloud: 'https://example.com/swe.png' },
    { noc: 'HKG', flag_url_cloud: 'https://example.com/hkg.png' },
    { noc: 'AUS', flag_url_cloud: 'https://example.com/aus.png' },
  ],
};

const RaisingFlagsWidget = ({ data }) => {
  const [selectedEventId, setSelectedEventId] = useState('');
  const [flags, setFlags] = useState([]);

  if (!data || !data.meta || !data.meta.events) {
    return <div>Loading event data...</div>;
  }

  const handleEventChange = (event) => {
    const eventId = event.target.value;
    setSelectedEventId(eventId);
    setFlags(mockFlagsByEvent[eventId] || []);
  };

  return (
    <Paper style={{ padding: '16px', margin: '16px' }}>
      <h2>Raising Flags</h2>
      <FormControl fullWidth margin="normal">
        <InputLabel id="event-select-flags-label">Select Event</InputLabel>
        <Select
          labelId="event-select-flags-label"
          value={selectedEventId}
          label="Select Event"
          onChange={handleEventChange}
        >
          {data.meta.events.map((event) => (
            <MenuItem key={event.event_id} value={event.event_id}>
              {event.name}
            </MenuItem>
          ))}
        </Select>
      </FormControl>

      {selectedEventId && (
        <Box display="flex" justifyContent="center" marginTop="16px">
          {flags.map((flag) => (
            <img key={flag.noc} src={flag.flag_url_cloud} alt={flag.noc} style={{ width: '100px', margin: '0 10px' }} />
          ))}
        </Box>
      )}
    </Paper>
  );
};

export default RaisingFlagsWidget;
