import React, { useState } from 'react';
import { Select, MenuItem, Paper, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, FormControl, InputLabel } from '@mui/material';

// Mock data, to be replaced by backend data.
const mockTeamStartListByUnit = {
  'SWMW4X200MFR----------FNL-000100--': [
    {
      lane: 1,
      team_name: 'Australia',
      noc: 'AUS',
      members: [
        { name: 'Iona Anderson' },
        { name: 'Shayna Jack' },
        { name: 'Brianna Throssell' },
        { name: 'Mollie O\'Callaghan' },
      ]
    },
  ],
};

const StartListTeamWidget = ({ data }) => {
  const [selectedUnitId, setSelectedUnitId] = useState('');
  const [startList, setStartList] = useState([]);

  if (!data || !data.meta || !data.meta.units) {
    return <div>Loading unit data...</div>;
  }

  const handleUnitChange = (event) => {
    const unitId = event.target.value;
    setSelectedUnitId(unitId);
    setStartList(mockTeamStartListByUnit[unitId] || []);
  };

  return (
    <Paper style={{ padding: '16px', margin: '16px' }}>
      <h2>Team Start List</h2>
      <FormControl fullWidth margin="normal">
        <InputLabel id="unit-select-team-label">Select Unit</InputLabel>
        <Select
          labelId="unit-select-team-label"
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
                <TableCell>Team</TableCell>
                <TableCell>NOC</TableCell>
                <TableCell>Members</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {startList.map((team) => (
                <TableRow key={team.lane}>
                  <TableCell>{team.lane}</TableCell>
                  <TableCell>{team.team_name}</TableCell>
                  <TableCell>{team.noc}</TableCell>
                  <TableCell>{team.members.map(m => m.name).join(', ')}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}
    </Paper>
  );
};

export default StartListTeamWidget;
