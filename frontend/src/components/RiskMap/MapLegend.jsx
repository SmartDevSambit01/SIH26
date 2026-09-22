import React, { useState } from 'react';
import { ChevronDown, ChevronUp, Layers } from 'lucide-react';
import { timeAgo } from './SystemStatusPill';

const STATUS_COLOR = {
  AVAILABLE: '#34D399',
  STALE: '#FBBF24',
};

function statusLine(entry) {
  if (!entry || !entry.status) return { text: 'Loading…', color: '#94A3B8' };
  const age = timeAgo(entry.timestamp);
  return {
    text: `${entry.status}${age ? ` · ${age}` : ''}`,
    color: STATUS_COLOR[entry.status] || '#F87171',
  };
}

export default function MapLegend({ dataStatus }) {
  const [collapsed, setCollapsed] = useState(false);
  const rain = statusLine(dataStatus?.rainfall);
  const soil = statusLine(dataStatus?.soil_moisture);

  const legendItems = [
    { label: 'Critical', color: '#9333EA', desc: 'Very High Susceptibility (Slope >35°, High Curvature)' },
    { label: 'High', color: '#EF4444', desc: 'High Susceptibility (Steep relief, low drainage capacity)' },
    { label: 'Warning', color: '#F97316', desc: 'Moderate Susceptibility (Moderate slope stability)' },
    { label: 'Watch', color: '#EAB308', desc: 'Low Susceptibility (Gentle slope, stable geology)' },
    { label: 'Low', color: '#10B981', desc: 'Very Low Susceptibility (Valley/plateau floor)' },
    { label: 'Risk Unavailable', color: '#4B5563', desc: 'Dynamic data stale / Unsurveyed cell' },
  ];

  return (
    <div className="map-legend-card">
      <div className="legend-title" onClick={() => setCollapsed(!collapsed)} style={{ cursor: 'pointer' }}>
        <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <Layers size={14} color="var(--c-coral)" />
          Risk Status &amp; 500m Grid
        </span>
        {collapsed ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
      </div>

      {!collapsed && (
        <>
          <div className="legend-items">
            {legendItems.map((item) => (
              <div key={item.label} className="legend-item" title={item.desc}>
                <div className="legend-color-box" style={{ backgroundColor: item.color }} />
                <span>{item.label}</span>
              </div>
            ))}
          </div>

          <div className="data-status-section" style={{ marginTop: '10px', paddingTop: '8px', borderTop: '1px solid var(--c-hairline-soft)', fontFamily: 'var(--font-body)', fontSize: '11px', color: 'var(--c-muted)', display: 'flex', flexDirection: 'column', gap: '4px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span>GPM Rainfall: <strong style={{ color: rain.color }}>{rain.text}</strong></span>
              <span style={{ color: 'var(--c-slate)' }}>Native ~10 km</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span>SMAP Soil Moisture: <strong style={{ color: soil.color }}>{soil.text}</strong></span>
              <span style={{ color: 'var(--c-slate)' }}>Native ~9 km</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span>Analysis Grid: <strong style={{ color: 'var(--c-blue)' }}>500m</strong></span>
              <span style={{ color: 'var(--c-slate)' }}>16,961 cells</span>
            </div>
          </div>

          <div className="legend-notice" style={{ marginTop: '8px', fontSize: '10px', color: 'var(--c-slate)', lineHeight: '1.4' }}>
            Dynamic risk uses available satellite observations when fresh data is available. Risk remains unavailable when required dynamic evidence is stale or missing.
          </div>
        </>
      )}
    </div>
  );
}
