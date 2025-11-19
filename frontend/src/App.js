import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './App.css';

import CountdownWidget from './components/CountdownWidget';
import ChampTitleWidget from './components/ChampTitleWidget';
import TimetableWidget from './components/TimetableWidget';
import EventIdWidget from './components/EventIdWidget';
import LaneIdWidget from './components/LaneIdWidget';
import TeamIdWidget from './components/TeamIdWidget';
import StartListIndWidget from './components/StartListIndWidget';
import StartListTeamWidget from './components/StartListTeamWidget';
import WinnerIdWidget from './components/WinnerIdWidget';
import NewRecordWidget from './components/NewRecordWidget';
import ResultsWidget from './components/ResultsWidget';
import QualifiersWidget from './components/QualifiersWidget';
import PhaseSummaryWidget from './components/PhaseSummaryWidget';
import CeremonyIdWidget from './components/CeremonyIdWidget';
import PresentersWidget from './components/PresentersWidget';
import MedalIdWidget from './components/MedalIdWidget';
import MedalListWidget from './components/MedalListWidget';
import MedalTallyWidget from './components/MedalTallyWidget';
import RaisingFlagsWidget from './components/RaisingFlagsWidget';
import ChampionshipInfoWidget from './components/ChampionshipInfoWidget';

function App() {
  const [data, setData] = useState(null);

  const fetchData = () => {
    axios.get('http://localhost:8000/all-data')
      .then(response => {
        setData(response.data);
      })
      .catch(error => {
        console.error('Error fetching data:', error);
      });
  };

  useEffect(() => {
    fetchData();

    const ws = new WebSocket('ws://localhost:8000/ws');
    ws.onmessage = (event) => {
      if (event.data === 'data updated') {
        fetchData();
      }
    };

    return () => {
      ws.close();
    };
  }, []);

  return (
    <div className="App">
      <h1>Dashboard</h1>
      <div className="dashboard-grid">
        <CountdownWidget data={data} />
        <ChampTitleWidget data={data} />
        <TimetableWidget data={data} />
        <EventIdWidget data={data} />
        <LaneIdWidget data={data} />
        <TeamIdWidget data={data} />
        <StartListIndWidget data={data} />
        <StartListTeamWidget data={data} />
        <WinnerIdWidget data={data} />
        <NewRecordWidget data={data} />
        <ResultsWidget data={data} />
        <QualifiersWidget data={data} />
        <PhaseSummaryWidget data={data} />
        <CeremonyIdWidget data={data} />
        <PresentersWidget data={data} />
        <MedalIdWidget data={data} />
        <MedalListWidget data={data} />
        <MedalTallyWidget data={data} />
        <RaisingFlagsWidget data={data} />
        <ChampionshipInfoWidget />
      </div>
    </div>
  );
}

export default App;
