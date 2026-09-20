import React, { useState, useEffect } from 'react';
import { MapPin, AlertCircle, ChevronRight } from 'lucide-react';

export default function AreaSearchPanel({ searchTerm, district, onSelectArea }) {
  const [results, setResults] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

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
    <div className="area-search-dropdown">
      {isLoading && (
        <div className="area-search-dropdown-empty">Searching locality index…</div>
      )}

      {error && (
        <div className="area-search-dropdown-empty" style={{ color: '#F87171', display: 'flex', alignItems: 'center', gap: 6, justifyContent: 'center' }}>
          <AlertCircle size={14} />
          <span>{error}</span>
        </div>
      )}

      {!isLoading && !error && results.length === 0 && (
        <div className="area-search-dropdown-empty">No recognized localities found for "{searchTerm}".</div>
      )}

      {!isLoading && !error && results.map((area) => (
        <div key={area.area_id} onClick={() => onSelectArea(area.area_id)} className="area-search-dropdown-item">
          <div>
            <div className="area-search-dropdown-name">
              <MapPin size={13} style={{ color: '#38BDF8', flexShrink: 0 }} />
              {area.area_name}
            </div>
            <div className="area-search-dropdown-meta">
              {area.district} · {area.place_type} · {area.cell_count} cells
            </div>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            {area.dominant_class && (
              <span
                className="area-search-dropdown-badge"
                style={{ color: getRiskBadgeColor(area.dominant_class), borderColor: `${getRiskBadgeColor(area.dominant_class)}50`, background: `${getRiskBadgeColor(area.dominant_class)}20` }}
              >
                {area.dominant_class}
              </span>
            )}
            <ChevronRight size={14} style={{ color: '#64748B' }} />
          </div>
        </div>
      ))}
    </div>
  );
}
