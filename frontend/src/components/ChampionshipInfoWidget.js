import React, { useState } from 'react';
import { TextField, Button, Paper } from '@mui/material';
import axios from 'axios';

const ChampionshipInfoWidget = () => {
  const [name, setName] = useState('');
  const [logoUrl, setLogoUrl] = useState('');
  const [websiteUrl, setWebsiteUrl] = useState('');

  const handleSubmit = () => {
    axios.post('http://localhost:8000/tournament-info', {
      name: name,
      logo_url_cloud: logoUrl,
      website_url: websiteUrl,
    })
    .then(response => {
      console.log('Championship info submitted successfully');
    })
    .catch(error => {
      console.error('Error submitting championship info:', error);
    });
  };

  return (
    <Paper>
      <h2>Championship Information</h2>
      <TextField label="Tournament Name" value={name} onChange={(e) => setName(e.target.value)} />
      <TextField label="Logo URL" value={logoUrl} onChange={(e) => setLogoUrl(e.target.value)} />
      <TextField label="Website URL" value={websiteUrl} onChange={(e) => setWebsiteUrl(e.target.value)} />
      <Button onClick={handleSubmit}>Submit</Button>
    </Paper>
  );
};

export default ChampionshipInfoWidget;
