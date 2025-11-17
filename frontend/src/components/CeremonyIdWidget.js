import React, { useState } from 'react';
import { Select, MenuItem, Paper, Typography, FormControl, InputLabel, TextField, Button } from '@mui/material';

// Mock data, to be replaced by backend data.
const mockCeremonies = {
  'CEREMONY01': { name: 'Men\'s 100m Freestyle Ceremony', event: 'Men\'s 100m Freestyle' },
  'CEREMONY02': { name: 'Women\'s 200m Butterfly Ceremony', event: 'Women\'s 200m Butterfly' },
};

const CeremonyIdWidget = ({ data }) => {
  const [selectedCeremonyId, setSelectedCeremonyId] = useState('');
  const [presenter, setPresenter] = useState('');
  const [notes, setNotes] = useState('');

  const handleCeremonyChange = (event) => {
    setSelectedCeremonyId(event.target.value);
  };

  const selectedCeremony = mockCeremonies[selectedCeremonyId];

  return (
    <Paper style={{ padding: '16px', margin: '16px' }}>
      <h2>Medal Ceremony</h2>
      <FormControl fullWidth margin="normal">
        <InputLabel id="ceremony-select-label">Select Ceremony</InputLabel>
        <Select
          labelId="ceremony-select-label"
          value={selectedCeremonyId}
          label="Select Ceremony"
          onChange={handleCeremonyChange}
        >
          {Object.entries(mockCeremonies).map(([id, ceremony]) => (
            <MenuItem key={id} value={id}>
              {ceremony.name}
            </MenuItem>
          ))}
        </Select>
      </FormControl>

      {selectedCeremony && (
        <div style={{ marginTop: '16px' }}>
          <Typography variant="h6">{selectedCeremony.name}</Typography>
          <TextField
            label="Presenter"
            value={presenter}
            onChange={(e) => setPresenter(e.target.value)}
            fullWidth
            margin="normal"
          />
          <TextField
            label="Notes"
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            fullWidth
            margin="normal"
            multiline
            rows={3}
          />
          <Button variant="contained">Save Manual Data</Button>
        </div>
      )}
    </Paper>
  );
};

export default CeremonyIdWidget;
