import React from 'react';
import { Layers, Eye, EyeOff, Search, Compass, MapPin } from 'lucide-react';

export default function DistrictSelector({
  selectedDistrict,
  onSelectDistrict,
  searchTerm,
  onSearchChange,
  onSearchSubmit,
  showGrid,
  onToggleGrid,
  showBoundary,
  onToggleBoundary,
  showHistorical,
  onToggleHistorical,
  showFlood,
  onToggleFlood,
  basemapType,
  onChangeBasemap,
}) {
  return (
    <div className="map-floating-panel">
      <div className="panel-header">
        <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <Layers size={14} color="var(--c-coral)" />
          Map Controls
        </span>
        <span style={{ fontSize: 11, color: 'var(--c-slate)' }}>500m Grid</span>
      </div>

      {/* Layer Visibility Toggles */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 6, marginBottom: 12 }}>
        <label className="layer-toggle-row">
          <span>500m Analysis Grid</span>
          <input
            type="checkbox"
            checked={showGrid}
            onChange={(e) => onToggleGrid(e.target.checked)}
          />
        </label>

        <label className="layer-toggle-row">
          <span>District Boundary</span>
          <input
            type="checkbox"
            checked={showBoundary}
            onChange={(e) => onToggleBoundary(e.target.checked)}
          />
        </label>

        <label className="layer-toggle-row">
          <span>Historical Events (11 Verified)</span>
          <input
            type="checkbox"
            checked={showHistorical}
            onChange={(e) => onToggleHistorical(e.target.checked)}
          />
        </label>

        <label className="layer-toggle-row">
          <span>Flash-Flood Susceptibility (Static)</span>
          <input
            type="checkbox"
            checked={showFlood}
            onChange={(e) => onToggleFlood(e.target.checked)}
          />
        </label>
      </div>

      {/* Basemap Switcher */}
      <div className="basemap-select-group">
        <div className="basemap-label">Basemap Style</div>
        <div className="basemap-pills">
          <button
            type="button"
            className={`basemap-pill-btn ${basemapType === 'satellite' ? 'active' : ''}`}
            onClick={() => onChangeBasemap('satellite')}
          >
            Satellite
          </button>
          <button
            type="button"
            className={`basemap-pill-btn ${basemapType === 'dark' ? 'active' : ''}`}
            onClick={() => onChangeBasemap('dark')}
          >
            Dark Vector
          </button>
        </div>
      </div>
    </div>
  );
}
