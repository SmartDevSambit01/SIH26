import React, { useState } from 'react';
import LandingPage from './components/LandingPage';
import RiskMapPage from './components/RiskMap/RiskMapPage';

function App() {
  const [currentPage, setCurrentPage] = useState('HOME');
  const [selectedDistrict, setSelectedDistrict] = useState('Kohima');
  const [openAlertsOnLoad, setOpenAlertsOnLoad] = useState(false);

  const handleNavigate = (page, district = null) => {
    if (page === 'ALERTS') {
      // The Alerts nav item opens the real, working alert dashboard that
      // otherwise only lived inside the Risk Map's toolbar toggle.
      setOpenAlertsOnLoad(true);
      setCurrentPage('RISK_MAP');
    } else {
      setOpenAlertsOnLoad(false);
      setCurrentPage(page);
    }
    if (district) {
      setSelectedDistrict(district);
    }
    window.scrollTo(0, 0);
  };

  if (currentPage === 'RISK_MAP' || currentPage === 'risk-map') {
    return (
      <RiskMapPage
        initialDistrict={selectedDistrict}
        initialShowAlerts={openAlertsOnLoad}
        onNavigate={handleNavigate}
      />
    );
  }

  return <LandingPage onNavigate={handleNavigate} />;
}

export default App;
