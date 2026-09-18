import React, { useState, useEffect } from 'react';
import { Search, MapPin, AlertCircle, ChevronRight, X } from 'lucide-react';

export default function AreaSearchPanel({ district, onSelectArea, onClose }) {
  const [searchTerm, setSearchTerm] = useState('');
  const [results, setResults] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  // Default featured localities when search is empty
  useEffect(() => {
    fetchAreas(searchTerm);
  }, [searchTerm, district]);

  const fetchAreas = async (term) => {
    setIsLoading(true);
    setError(null);

    let path = `/api/areas?limit=25`;
    if (term && term.trim()) {
      // Cross-district search: do not restrict by district when a term is provided
      path += `&search=${encodeURIComponent(term.trim())}`;
    } else if (district) {
      // Featured localities view: restrict to current district when search is empty
      path += `&district=${encodeURIComponent(district)}`;
    }

    const hosts = [
      import.meta.env.VITE_API_URL || '',
      'http://127.0.0.1:8000',
      'http://localhost:8000'
    ];

    let lastErr = null;
    let data = null;

    for (const host of hosts) {
      try {
        const url = host ? `${host}${path}` : path;
        const res = await fetch(url);
        if (res.ok) {
          data = await res.json();
          break;
        }
      } catch (err) {
        lastErr = err;
      }
    }

    if (data) {
      setResults(data);
      setIsLoading(false);
    } else {
      console.error('Error fetching areas:', lastErr);
      setError('Unable to load area index from API backend.');
      setIsLoading(false);
    }
  };

  const getRiskBadgeColor = (cls) => {
    switch (cls) {
      case 'VERY_HIGH': return '#DC2626';
      case 'HIGH': return '#EF4444';
      case 'MODERATE': return '#F59E0B';
      case 'LOW': return '#10B981';
      case 'VERY_LOW': return '#059669';
      default: return '#6B7280';
    }
  };

  return (
    <div className="area-search-panel" style={{
      padding: '16px',
      background: 'rgba(15, 23, 42, 0.95)',
      borderRadius: '12px',
      border: '1px solid rgba(255, 255, 255, 0.12)',
      boxShadow: '0 8px 32px rgba(0,0,0,0.4)',
      width: '360px',
      maxHeight: '480px',
      display: 'flex',
      flexDirection: 'column',
      gap: '12px'
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h4 style={{ margin: 0, fontSize: '14px', fontWeight: 600, color: '#F8FAFC', display: 'flex', alignItems: 'center', gap: '6px' }}>
          <MapPin size={16} style={{ color: '#38BDF8' }} />
          <span>Area / Locality Search</span>
        </h4>
        {onClose && (
          <button 
            type="button" 
            onClick={onClose} 
            style={{ background: 'none', border: 'none', color: '#94A3B8', cursor: 'pointer', padding: '4px' }}
          >
            <X size={16} />
          </button>
        )}
      </div>

      <div className="search-input-box" style={{ position: 'relative' }}>
        <Search size={15} style={{ position: 'absolute', left: '10px', top: '50%', transform: 'translateY(-50%)', color: '#64748B' }} />
        <input
          type="text"
          placeholder="Search area (e.g. Durtlang, Khonoma, Merima)..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          style={{
            width: '100%',
            padding: '8px 10px 8px 32px',
            background: 'rgba(30, 41, 59, 0.8)',
            border: '1px solid rgba(255, 255, 255, 0.15)',
            borderRadius: '6px',
            color: '#F1F5F9',
            fontSize: '13px',
            outline: 'none'
          }}
        />
      </div>

      {isLoading && (
        <div style={{ fontSize: '12px', color: '#94A3B8', textAlign: 'center', padding: '12px' }}>
          Searching OSM locality index...
        </div>
      )}

      {error && (
        <div style={{ fontSize: '12px', color: '#F87171', display: 'flex', alignItems: 'center', gap: '6px', padding: '8px' }}>
          <AlertCircle size={14} />
          <span>{error}</span>
        </div>
      )}

      {!isLoading && !error && results.length === 0 && (
        <div style={{ fontSize: '12px', color: '#64748B', textAlign: 'center', padding: '12px' }}>
          No recognized localities found for "{searchTerm}" in {district || 'all districts'}.
        </div>
      )}

      <div className="area-results-list" style={{
        overflowY: 'auto',
        display: 'flex',
        flexDirection: 'column',
        gap: '8px',
        maxHeight: '340px'
      }}>
        {results.map((area) => (
          <div
            key={area.area_id}
            onClick={() => onSelectArea(area.area_id)}
            style={{
              padding: '10px 12px',
              background: 'rgba(30, 41, 59, 0.6)',
              borderRadius: '8px',
              border: '1px solid rgba(255, 255, 255, 0.08)',
              cursor: 'pointer',
              transition: 'all 0.15s ease',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center'
            }}
            className="area-item-card"
          >
            <div>
              <div style={{ fontSize: '13px', fontWeight: 600, color: '#F8FAFC', display: 'flex', alignItems: 'center', gap: '6px' }}>
                📍 {area.area_name}
              </div>
              <div style={{ fontSize: '11px', color: '#94A3B8', marginTop: '2px' }}>
                District: <strong>{area.district}</strong> • Type: <span style={{ textTransform: 'capitalize' }}>{area.place_type}</span>
              </div>
              <div style={{ fontSize: '11px', color: '#CBD5E1', marginTop: '4px', display: 'flex', gap: '10px' }}>
                <span>Cells: <strong>{area.cell_count}</strong></span>
                <span>Max TSI: <strong>{area.max_tsi !== null ? area.max_tsi : 'N/A'}</strong></span>
              </div>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '4px' }}>
              {area.dominant_class && (
                <span style={{
                  fontSize: '10px',
                  fontWeight: 700,
                  padding: '2px 6px',
                  borderRadius: '4px',
                  background: `${getRiskBadgeColor(area.dominant_class)}25`,
                  color: getRiskBadgeColor(area.dominant_class),
                  border: `1px solid ${getRiskBadgeColor(area.dominant_class)}50`
                }}>
                  {area.dominant_class}
                </span>
              )}
              <ChevronRight size={14} style={{ color: '#64748B' }} />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
