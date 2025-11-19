import React, { useState } from 'react';
import { Select, MenuItem, Paper, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, FormControl, InputLabel } from '@mui/material';

// Mock data, to be replaced by backend data.
const mockPhaseSummary = {
  'SWMW100MFR----------': {
    'Heats': [
      { name: 'Sarah Sjostrom', noc: 'SWE', time: '52.00' },
      { name: 'Siobhan Haughey', noc: 'HKG', time: '52.50' },
    ],
    'Final': [
      { name: 'Sarah Sjostrom', noc: 'SWE', time: '51.71' },
      { name: 'Siobhan Haughey', noc: 'HKG', time: '52.27' },
    ]
  }
};

const PhaseSummaryWidget = ({ data }) => {
  const [selectedEventId, setSelectedEventId] = useState('');
  const [selectedPhase, setSelectedPhase] = useState('');
  const [summary, setSummary] = useState([]);
  const [availablePhases, setAvailablePhases] = useState([]);

  if (!data || !data.meta || !data.meta.events) {
    return <div>Loading event data...</div>;
  }

  const handleEventChange = (event) => {
    const eventId = event.target.value;
    setSelectedEventId(eventId);
    setSelectedPhase('');
    setSummary([]);
    const phases = Object.keys(mockPhaseSummary[eventId] || {});
    setAvailablePhases(phases);
  };

  const handlePhaseChange = (event) => {
    const phase = event.target.value;
    setSelectedPhase(phase);
    setSummary(mockPhaseSummary[selectedEventId][phase] || []);
  };

  return (
    <Paper style={{ padding: '16px', margin: '16px' }}>
      <h2>Phase Summary</h2>
      <FormControl fullWidth margin="normal">
        <InputLabel id="event-select-summary-label">Select Event</InputLabel>
        <Select
          labelId="event-select-summary-label"
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

      <FormControl fullWidth margin="normal" disabled={!selectedEventId}>
        <InputLabel id="phase-select-label">Select Phase</InputLabel>
        <Select
          labelId="phase-select-label"
          value={selectedPhase}
          label="Select Phase"
          onChange={handlePhaseChange}
        >
          {availablePhases.map((phase) => (
            <MenuItem key={phase} value={phase}>
              {phase}
            </MenuItem>
          ))}
        </Select>
      </FormControl>

      {selectedPhase && (
        <TableContainer>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Name</TableCell>
                <TableCell>NOC</TableCell>
                <TableCell>Time</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {summary.map((row) => (
                <TableRow key={row.name}>
                  <TableCell>{row.name}</TableCell>
                  <TableCell>{row.noc}</TableCell>
                  <TableCell>{row.time}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}
    </Paper>
  );
};

export default PhaseSummaryWidget;
