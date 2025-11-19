import React, { useState } from 'react';
import { Select, MenuItem, Paper, Typography, FormControl, InputLabel } from '@mui/material';

const EventIdWidget = ({ data }) => {
  const [selectedEventId, setSelectedEventId] = useState('');

  if (!data || !data.meta || !data.meta.events) {
    return <div>Loading event data...</div>;
  }

  const handleEventChange = (event) => {
    setSelectedEventId(event.target.value);
  };

  const selectedEvent = data.meta.events.find(e => e.event_id === selectedEventId);

  return (
    <Paper style={{ padding: '16px', margin: '16px' }}>
      <h2>Event Details</h2>
      <FormControl fullWidth>
        <InputLabel id="event-select-label">Select Event</InputLabel>
        <Select
          labelId="event-select-label"
          id="event-select"
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
      {selectedEvent && (
        <div style={{ marginTop: '16px' }}>
          <Typography variant="h6">{selectedEvent.name}</Typography>
          <Typography><strong>ID:</strong> {selectedEvent.event_id}</Typography>
          <Typography><strong>Gender:</strong> {selectedEvent.gender}</Typography>
          <Typography><strong>Stroke:</strong> {selectedEvent.stroke}</Typography>
          <Typography><strong>Distance:</strong> {selectedEvent.distance}</Typography>
        </div>
      )}
    </Paper>
  );
};

export default EventIdWidget;
