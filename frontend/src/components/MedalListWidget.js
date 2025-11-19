import React, { useState } from 'react';
import { Select, MenuItem, Paper, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, FormControl, InputLabel } from '@mui/material';

// Mock data, to be replaced by backend data.
const mockMedalistsByEvent = {
  'SWMW100MFR----------': [
    { medal: 'Gold', name: 'Sarah Sjostrom', noc: 'SWE' },
    { medal: 'Silver', name: 'Siobhan Haughey', noc: 'HKG' },
    { medal: 'Bronze', name: 'Emma McKeon', noc: 'AUS' },
  ],
};

const MedalListWidget = ({ data }) => {
  const [selectedEventId, setSelectedEventId] = useState('');
  const [medalists, setMedalists] = useState([]);

  if (!data || !data.meta || !data.meta.events) {
    return <div>Loading event data...</div>;
  }

  const handleEventChange = (event) => {
    const eventId = event.target.value;
    setSelectedEventId(eventId);
    setMedalists(mockMedalistsByEvent[eventId] || []);
  };

  return (
    <Paper style={{ padding: '16px', margin: '16px' }}>
      <h2>Medal List</h2>
      <FormControl fullWidth margin="normal">
        <InputLabel id="event-select-medals-label">Select Event</InputLabel>
        <Select
          labelId="event-select-medals-label"
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
        <TableContainer>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Medal</TableCell>
                <TableCell>Name</TableCell>
                <TableCell>NOC</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {medalists.map((medalist) => (
                <TableRow key={medalist.medal}>
                  <TableCell>{medalist.medal}</TableCell>
                  <TableCell>{medalist.name}</TableCell>
                  <TableCell>{medalist.noc}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}
    </Paper>
  );
};

export default MedalListWidget;
