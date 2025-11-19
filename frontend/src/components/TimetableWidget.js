import React from 'react';
import { Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Paper } from '@mui/material';

const TimetableWidget = ({ data }) => {
  if (!data || !data.timetable) {
    return <div>Loading...</div>;
  }

  return (
    <Paper>
      <h2>Timetable</h2>
      <TableContainer>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Start Time</TableCell>
              <TableCell>Event</TableCell>
              <TableCell>Phase</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {data.timetable.map((row, index) => (
              <TableRow key={index}>
                <TableCell>{new Date(row.start_time).toLocaleString()}</TableCell>
                <TableCell>{row.event}</TableCell>
                <TableCell>{row.phase}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    </Paper>
  );
};

export default TimetableWidget;
