import React, { useState, useEffect } from 'react';
import { Select, MenuItem, Paper, Typography, FormControl, InputLabel } from '@mui/material';

// This is mock data until the backend provides the real data.
const mockTeamsByEvent = {
  'SWMW100MFR----------': [
    { participant_id: 'TEAMUSA', name: 'USA Swimming Team' },
    { participant_id: 'TEAMAUS', name: 'Australia Swimming Team' },
  ],
  'SWMW200MFR----------': [
    { participant_id: 'TEAMGBR', name: 'Great Britain Swimming' },
    { participant_id: 'TEAMCHN', name: 'China Swimming Team' },
  ],
};

const TeamIdWidget = ({ data }) => {
  const [selectedEventId, setSelectedEventId] = useState('');
  const [selectedTeamId, setSelectedTeamId] = useState('');
  const [availableTeams, setAvailableTeams] = useState([]);
  const [selectedTeam, setSelectedTeam] = useState(null);

  if (!data || !data.meta || !data.meta.events) {
    return <div>Loading event data...</div>;
  }

  const handleEventChange = (event) => {
    const eventId = event.target.value;
    setSelectedEventId(eventId);
    setSelectedTeamId('');
    setSelectedTeam(null);
    // In the future, this data will come from the main JSON object.
    setAvailableTeams(mockTeamsByEvent[eventId] || []);
  };

  const handleTeamChange = (event) => {
    const teamId = event.target.value;
    setSelectedTeamId(teamId);
    const team = availableTeams.find(t => t.participant_id === teamId);
    setSelectedTeam(team);
  };

  return (
    <Paper style={{ padding: '16px', margin: '16px' }}>
      <h2>Team Details</h2>
      <FormControl fullWidth margin="normal">
        <InputLabel id="event-select-team-label">Select Event</InputLabel>
        <Select
          labelId="event-select-team-label"
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
        <InputLabel id="team-select-label">Select Team</InputLabel>
        <Select
          labelId="team-select-label"
          value={selectedTeamId}
          label="Select Team"
          onChange={handleTeamChange}
        >
          {availableTeams.map((team) => (
            <MenuItem key={team.participant_id} value={team.participant_id}>
              {team.name}
            </MenuItem>
          ))}
        </Select>
      </FormControl>

      {selectedTeam && (
        <div style={{ marginTop: '16px' }}>
          <Typography variant="h6">{selectedTeam.name}</Typography>
          <Typography><strong>ID:</strong> {selectedTeam.participant_id}</Typography>
        </div>
      )}
    </Paper>
  );
};

export default TeamIdWidget;
