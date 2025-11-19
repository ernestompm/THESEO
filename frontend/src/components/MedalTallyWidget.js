import React, { useState } from 'react';
import { Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Paper, Select, MenuItem } from '@mui/material';

const MedalTallyWidget = ({ data }) => {
  const [rowsToShow, setRowsToShow] = useState(10);

  if (!data || !data.medal_tally) {
    return <div>Loading...</div>;
  }

  const handleChange = (event) => {
    setRowsToShow(event.target.value);
  };

  return (
    <Paper>
      <h2>Medal Tally</h2>
      <Select value={rowsToShow} onChange={handleChange}>
        <MenuItem value={5}>5</MenuItem>
        <MenuItem value={10}>10</MenuItem>
        <MenuItem value={15}>15</MenuItem>
      </Select>
      <TableContainer>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Rank</TableCell>
              <TableCell>Flag</TableCell>
              <TableCell>NOC</TableCell>
              <TableCell>Name</TableCell>
              <TableCell>Gold</TableCell>
              <TableCell>Silver</TableCell>
              <TableCell>Bronze</TableCell>
              <TableCell>Total</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {data.medal_tally.slice(0, rowsToShow).map((row) => (
              <TableRow key={row.noc}>
                <TableCell>{row.rank}</TableCell>
                <TableCell><img src={row.flag} alt={row.noc} width="30" /></TableCell>
                <TableCell>{row.noc}</TableCell>
                <TableCell>{row.name}</TableCell>
                <TableCell>{row.golds}</TableCell>
                <TableCell>{row.silvers}</TableCell>
                <TableCell>{row.bronzes}</TableCell>
                <TableCell>{row.total}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    </Paper>
  );
};

export default MedalTallyWidget;
