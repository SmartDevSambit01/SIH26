import React, { useState } from 'react';
import LandingPage from './components/LandingPage';
import RiskMapPage from './components/RiskMap/RiskMapPage';

function App() {
  const [currentPage, setCurrentPage] = useState('HOME');
  const [selectedDistrict, setSelectedDistrict] = useState('Kohima');

  const handleNavigate = (page, district = null) => {
    setCurrentPage(page);
    if (district) {
      setSelectedDistrict(district);
    }
    window.scrollTo(0, 0);
  };

  if (currentPage === 'RISK_MAP' || currentPage === 'risk-map') {
    return (
      <RiskMapPage
        initialDistrict={selectedDistrict}
        onNavigate={handleNavigate}
      />
    );
  }

  return <LandingPage onNavigate={handleNavigate} />;
}

export default App;
