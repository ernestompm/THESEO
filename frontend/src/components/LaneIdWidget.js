import React, { useState } from 'react';
import { Select, MenuItem, Paper, Typography, FormControl, InputLabel } from '@mui/material';

// Mock data: In a real scenario, this would come from the main JSON object.
// It maps a unit_id to a list of participants in specific lanes.
const mockStartListByUnit = {
  'SWMW4X200MFR----------FNL-000100--': [
    { lane: 1, participant_id: '1946183', name: 'Iona Anderson', noc: 'AUS' },
    { lane: 2, participant_id: '1946184', name: 'Shayna Jack', noc: 'AUS' },
    { lane: 3, participant_id: '1946185', name: 'Brianna Throssell', noc: 'AUS' },
    { lane: 4, participant_id: '1946186', name: 'Mollie O\'Callaghan', noc: 'AUS' },
  ],
  'SWMW100MFR----------FNL-000100--': [
    { lane: 1, participant_id: '2000001', name: 'Sarah Sjostrom', noc: 'SWE' },
    { lane: 2, participant_id: '2000002', name: 'Siobhan Haughey', noc: 'HKG' },
  ]
};

const LaneIdWidget = ({ data }) => {
  const [selectedUnitId, setSelectedUnitId] = useState('');
  const [selectedLane, setSelectedLane] = useState('');
  const [availableLanes, setAvailableLanes] = useState([]);
  const [participant, setParticipant] = useState(null);

  if (!data || !data.meta || !data.meta.units) {
    return <div>Loading unit data...</div>;
  }

  const handleUnitChange = (event) => {
    const unitId = event.target.value;
    setSelectedUnitId(unitId);
    setSelectedLane('');
    setParticipant(null);
    // Use mock data to populate available lanes for the selected unit
    const startList = mockStartListByUnit[unitId] || [];
    setAvailableLanes(startList);
  };

  const handleLaneChange = (event) => {
    const laneNumber = event.target.value;
    setSelectedLane(laneNumber);
    const participantData = availableLanes.find(p => p.lane === laneNumber);
    setParticipant(participantData);
  };

  return (
    <Paper style={{ padding: '16px', margin: '16px' }}>
      <h2>Lane Details</h2>
      <FormControl fullWidth margin="normal">
        <InputLabel id="unit-select-label">Select Unit</InputLabel>
        <Select
          labelId="unit-select-label"
          value={selectedUnitId}
          label="Select Unit"
          onChange={handleUnitChange}
        >
          {data.meta.units.map((unit) => (
            <MenuItem key={unit.unit_id} value={unit.unit_id}>
              {unit.name || unit.unit_id}
            </MenuItem>
          ))}
        </Select>
      </FormControl>

      <FormControl fullWidth margin="normal" disabled={!selectedUnitId}>
        <InputLabel id="lane-select-label">Select Lane</InputLabel>
        <Select
          labelId="lane-select-label"
          value={selectedLane}
          label="Select Lane"
          onChange={handleLaneChange}
        >
          {availableLanes.map((p) => (
            <MenuItem key={p.lane} value={p.lane}>
              Lane {p.lane}
            </MenuItem>
          ))}
        </Select>
      </FormControl>

      {participant && (
        <div style={{ marginTop: '16px' }}>
          <Typography variant="h6">{participant.name}</Typography>
          <Typography><strong>ID:</strong> {participant.participant_id}</Typography>
          <Typography><strong>NOC:</strong> {participant.noc}</Typography>
          <Typography><strong>Lane:</strong> {participant.lane}</Typography>
        </div>
      )}
    </Paper>
  );
};

export default LaneIdWidget;
