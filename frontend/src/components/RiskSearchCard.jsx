import React, { useState } from 'react';
import { Search } from 'lucide-react';

export default function RiskSearchCard({ onNavigate }) {
  const [searchValue, setSearchValue] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    const query = searchValue.trim();
    if (onNavigate) {
      const isAizawl = query.toLowerCase().includes('aizawl') || query.toUpperCase().startsWith('AIZ_');
      onNavigate('RISK_MAP', isAizawl ? 'Aizawl' : 'Kohima');
    } else if (query) {
      alert(`Checking landslide risk for: "${query}"`);
    }
  };

  return (
    <div className="ner-search-card">
      <h2 className="ner-search-title">Check Risk in Your Area</h2>
      <form className="ner-search-form" onSubmit={handleSubmit}>
        <div className="ner-search-input-wrapper">
          <Search className="ner-search-input-icon" size={19} />
          <input
            type="text"
            className="ner-search-input"
            value={searchValue}
            onChange={(e) => setSearchValue(e.target.value)}
            placeholder="Search Location (e.g. Dibrugarh, Kohima...)"
            aria-label="Search location for landslide risk"
          />
        </div>
        <button type="submit" className="ner-btn-get-details">
          Get Details
        </button>
      </form>
    </div>
  );
}
