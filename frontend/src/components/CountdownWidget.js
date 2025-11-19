import React, { useState, useEffect } from 'react';
import { TextField, Button, Paper, Typography } from '@mui/material';

const CountdownWidget = () => {
  const [targetTime, setTargetTime] = useState('');
  const [remainingTime, setRemainingTime] = useState('');

  useEffect(() => {
    if (!targetTime) return;

    const interval = setInterval(() => {
      const now = new Date().getTime();
      const target = new Date(targetTime).getTime();
      const difference = target - now;

      if (difference <= 0) {
        setRemainingTime('00:00:00:00');
        clearInterval(interval);
        return;
      }

      const days = Math.floor(difference / (1000 * 60 * 60 * 24));
      const hours = Math.floor((difference % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
      const minutes = Math.floor((difference % (1000 * 60 * 60)) / (1000 * 60));
      const seconds = Math.floor((difference % (1000 * 60)) / 1000);

      setRemainingTime(
        `${String(days).padStart(2, '0')}:${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`
      );
    }, 1000);

    return () => clearInterval(interval);
  }, [targetTime]);

  return (
    <Paper style={{ padding: '16px', margin: '16px' }}>
      <h2>Countdown</h2>
      <TextField
        label="Target Time"
        type="datetime-local"
        value={targetTime}
        onChange={(e) => setTargetTime(e.target.value)}
        InputLabelProps={{
          shrink: true,
        }}
        style={{ marginRight: '16px' }}
      />
      <Typography variant="h4" style={{ marginTop: '16px' }}>
        {remainingTime || 'Set a target time'}
      </Typography>
    </Paper>
  );
};

export default CountdownWidget;
