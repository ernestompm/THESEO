import React, { useState } from 'react';
import { Select, MenuItem, Paper, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, FormControl, InputLabel } from '@mui/material';

// Mock data, to be replaced by backend data.
const mockQualifiersByUnit = {
  'SWMW100MFR----------FNL-000100--': [
    { name: 'Sarah Sjostrom', noc: 'SWE', time: '51.71', qualification: 'Q' },
    { name: 'Siobhan Haughey', noc: 'HKG', time: '52.27', qualification: 'Q' },
  ],
};

const QualifiersWidget = ({ data }) => {
  const [selectedUnitId, setSelectedUnitId] = useState('');
  const [qualifiers, setQualifiers] = useState([]);

  if (!data || !data.meta || !data.meta.units) {
    return <div>Loading unit data...</div>;
  }

  const handleUnitChange = (event) => {
    const unitId = event.target.value;
    setSelectedUnitId(unitId);
    setQualifiers(mockQualifiersByUnit[unitId] || []);
  };

  return (
    <Paper style={{ padding: '16px', margin: '16px' }}>
      <h2>Qualifiers</h2>
      <FormControl fullWidth margin="normal">
        <InputLabel id="unit-select-qualifiers-label">Select Unit</InputLabel>
        <Select
          labelId="unit-select-qualifiers-label"
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
                <TableCell>Name</TableCell>
                <TableCell>NOC</TableCell>
                <TableCell>Time</TableCell>
                <TableCell>Qualification</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {qualifiers.map((qualifier) => (
                <TableRow key={qualifier.name}>
                  <TableCell>{qualifier.name}</TableCell>
                  <TableCell>{qualifier.noc}</TableCell>
                  <TableCell>{qualifier.time}</TableCell>
                  <TableCell>{qualifier.qualification}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}
    </Paper>
  );
};

export default QualifiersWidget;
