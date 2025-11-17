import React, { useState } from 'react';
import { Select, MenuItem, Paper, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, FormControl, InputLabel, Typography } from '@mui/material';

// Mock data, to be replaced by backend data.
const mockResultsByUnit = {
  'SWMW100MFR----------FNL-000100--': [
    { rank: 1, name: 'Sarah Sjostrom', noc: 'SWE', time: '51.71', record: 'WR' },
    { rank: 2, name: 'Siobhan Haughey', noc: 'HKG', time: '52.27', record: '' },
  ],
};

const ResultsWidget = ({ data }) => {
  const [selectedUnitId, setSelectedUnitId] = useState('');
  const [results, setResults] = useState([]);

  if (!data || !data.meta || !data.meta.units) {
    return <div>Loading unit data...</div>;
  }

  const handleUnitChange = (event) => {
    const unitId = event.target.value;
    setSelectedUnitId(unitId);
    setResults(mockResultsByUnit[unitId] || []);
  };

  return (
    <Paper style={{ padding: '16px', margin: '16px' }}>
      <h2>Results</h2>
      <FormControl fullWidth margin="normal">
        <InputLabel id="unit-select-results-label">Select Unit</InputLabel>
        <Select
          labelId="unit-select-results-label"
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
                <TableCell>Rank</TableCell>
                <TableCell>Name</TableCell>
                <TableCell>NOC</TableCell>
                <TableCell>Time</TableCell>
                <TableCell>Record</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {results.map((result) => (
                <TableRow key={result.rank} style={result.record ? { backgroundColor: 'lightyellow' } : {}}>
                  <TableCell>{result.rank}</TableCell>
                  <TableCell>{result.name}</TableCell>
                  <TableCell>{result.noc}</TableCell>
                  <TableCell>{result.time}</TableCell>
                  <TableCell>
                    {result.record && <Typography color="error" variant="body2">{result.record}</Typography>}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}
    </Paper>
  );
};

export default ResultsWidget;
