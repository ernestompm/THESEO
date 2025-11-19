import React, { useState } from 'react';
import { Select, MenuItem, Paper, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, FormControl, InputLabel } from '@mui/material';

// Mock data, to be replaced by backend data.
const mockStartListByUnit = {
  'SWMW100MFR----------FNL-000100--': [
    { lane: 1, participant_id: '2000001', name: 'Sarah Sjostrom', noc: 'SWE' },
    { lane: 2, participant_id: '2000002', name: 'Siobhan Haughey', noc: 'HKG' },
  ],
  'SWMW200MFR----------FNL-000100--': [
      // Add individual participants if needed for this event
  ]
};

const StartListIndWidget = ({ data }) => {
  const [selectedUnitId, setSelectedUnitId] = useState('');
  const [startList, setStartList] = useState([]);

  if (!data || !data.meta || !data.meta.units) {
    return <div>Loading unit data...</div>;
  }

  const handleUnitChange = (event) => {
    const unitId = event.target.value;
    setSelectedUnitId(unitId);
    setStartList(mockStartListByUnit[unitId] || []);
  };

  return (
    <Paper style={{ padding: '16px', margin: '16px' }}>
      <h2>Individual Start List</h2>
      <FormControl fullWidth margin="normal">
        <InputLabel id="unit-select-ind-label">Select Unit</InputLabel>
        <Select
          labelId="unit-select-ind-label"
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

      {selectedUnitId && (
        <TableContainer>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Lane</TableCell>
                <TableCell>Name</TableCell>
                <TableCell>NOC</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {startList.map((participant) => (
                <TableRow key={participant.participant_id}>
                  <TableCell>{participant.lane}</TableCell>
                  <TableCell>{participant.name}</TableCell>
                  <TableCell>{participant.noc}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}
    </Paper>
  );
};

export default StartListIndWidget;
