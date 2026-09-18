import React, { useState, useEffect } from 'react';
import { X, MapPin, Mountain, CloudRain, Droplets, Radio, ShieldAlert, Users, Compass, AlertCircle, Cpu, BookOpen, CheckCircle, HelpCircle } from 'lucide-react';

export default function CellDetailsModal({ cell, onClose }) {
  if (!cell) return null;

  const {
    cell_id,
    district,
    centroid_lat,
    centroid_lon,
    risk_class,
    risk_badge,
    risk_color,
    tsi_score,
    tsi_class,
    elevation_m,
    elevation_min,
    elevation_max,
    slope_deg,
    slope_max_deg,
    aspect_deg,
    curvature,
    twi,
    pu_similarity,
    primary_contributors,
    has_verified_event,
    event_id,
    event_location,
    event_date,
    event_description,
  } = cell;

  const [aiPrediction, setAiPrediction] = useState(null);
  const [cellParameters, setCellParameters] = useState(null);
  const [cellRisk, setCellRisk] = useState(null);

  useEffect(() => {
    if (!cell_id) return;
    const baseUrl = import.meta.env.VITE_API_URL || '';

    fetch(`${baseUrl}/api/model/predictions/${cell_id}`)
      .then(res => res.ok ? res.json() : null)
      .then(data => setAiPrediction(data))
      .catch(() => setAiPrediction(null));

    fetch(`${baseUrl}/api/cells/${cell_id}/parameters`)
      .then(res => res.ok ? res.json() : null)
      .then(data => setCellParameters(data))
      .catch(() => setCellParameters(null));

    fetch(`${baseUrl}/api/cells/${cell_id}/risk`)
      .then(res => res.ok ? res.json() : null)
      .then(data => setCellRisk(data))
      .catch(() => setCellRisk(null));
  }, [cell_id]);

  const unavailableNotice = "Unavailable — external data/authentication required";
  const smapData = cellParameters?.soil_moisture;

  return (
    <aside className="cell-details-drawer">
      {/* Header */}
      <div className="drawer-header">
        <div>
          <h2 className="drawer-cell-title">
            <span>{cell_id}</span>
            <span
              className="cell-risk-badge"
              style={{ backgroundColor: risk_color, color: risk_class === 'WATCH' ? '#000000' : '#FFFFFF' }}
            >
              {risk_badge || risk_class}
            </span>
          </h2>
          <div className="drawer-subtitle">
            {district} District • {centroid_lat?.toFixed(5)}°N, {centroid_lon?.toFixed(5)}°E
          </div>
        </div>
        <button type="button" className="close-drawer-btn" onClick={onClose} aria-label="Close cell details">
          <X size={18} />
        </button>
      </div>

      <div className="drawer-content">
        {/* Historical Verified Event Alert (if present) */}
        {has_verified_event && (
          <div className="historical-alert-box">
            <h4 className="historical-alert-title">
              <ShieldAlert size={16} />
              Confirmed Historical Landslide Site ({event_id})
            </h4>
            <p className="historical-alert-desc">
              <strong>Location:</strong> {event_location} ({event_date})<br />
              <strong>Incident Log:</strong> {event_description}
            </p>
          </div>
        )}

        {/* AI Risk Assessment Card (Task 12) */}
        <div className="section-card" style={{ border: '1px solid rgba(56, 189, 248, 0.3)', background: 'rgba(15, 23, 42, 0.85)' }}>
          <h3 className="section-card-title">
            <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <Cpu size={16} color="#38BDF8" />
              AI Hazard & Risk Assessment
            </span>
            <span className="section-status-tag" style={{ background: 'rgba(245, 158, 11, 0.2)', color: '#FCD34D', border: '1px solid rgba(245, 158, 11, 0.4)' }}>
              Limited-Data Prototype
            </span>
          </h3>

          <div className="metrics-grid">
            <div className="metric-box">
              <div className="metric-label">Model Strategy</div>
              <div className="metric-value" style={{ fontSize: 11, color: '#38BDF8' }}>
                Static TSI + PU Metric
              </div>
            </div>

            <div className="metric-box">
              <div className="metric-label">Hazard Probability</div>
              <div className="metric-value unavailable-text" style={{ fontSize: 12 }}>
                {aiPrediction?.hazard_probability !== null ? aiPrediction?.hazard_probability : 'Unavailable'}
              </div>
            </div>

            <div className="metric-box full-width-metric">
              <div className="metric-label">Calibration Status</div>
              <div className="metric-value" style={{ fontSize: 11, color: '#FCD34D' }}>
                {aiPrediction?.calibration_status || 'NOT_CALIBRATED_REQUIRES_VERIFIED_EVENTS'}
              </div>
            </div>

            <div className="metric-box full-width-metric">
              <div className="metric-label">Top Contributing Evidence Factors</div>
              <div style={{ fontSize: 11, color: '#E2E8F0', marginTop: 4, display: 'flex', flexDirection: 'column', gap: 4 }}>
                {aiPrediction?.top_contributing_factors.map((f, i) => (
                  <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                    <CheckCircle size={12} color="#10B981" />
                    <span>{f}</span>
                  </div>
                )) || <div>Baseline terrain susceptibility score: {tsi_score || 'N/A'}</div>}
              </div>
            </div>

            {/* Parameter Range Evidence Comparison vs Peer-Reviewed Literature */}
            {aiPrediction?.parameter_comparisons && (
              <div className="metric-box full-width-metric" style={{ background: 'rgba(30, 41, 59, 0.5)', padding: 10, borderRadius: 6 }}>
                <div className="metric-label" style={{ display: 'flex', alignItems: 'center', gap: 4, color: '#94A3B8', marginBottom: 6 }}>
                  <BookOpen size={13} color="#F59E0B" />
                  <span>Parameter Evidence Comparison vs Literature Range</span>
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 6, fontSize: 11 }}>
                  {aiPrediction.parameter_comparisons.map((item, idx) => (
                    <div key={idx} style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid rgba(255,255,255,0.05)', paddingBottom: 4 }}>
                      <span style={{ color: '#CBD5E1', fontWeight: 500 }}>{item.parameter_name}:</span>
                      <div style={{ textAlign: 'right' }}>
                        <div style={{ color: item.current_value.includes('Unavailable') ? '#F59E0B' : '#38BDF8', fontWeight: 600 }}>
                          {item.current_value}
                        </div>
                        <div style={{ fontSize: 10, color: '#94A3B8' }}>
                          Ref: {item.reference_evidence_range}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Dynamic Risk Engine Assessment */}
        {cellRisk && (
          <div className="section-card" style={{ border: `1px solid ${cellRisk.risk_color || '#38BDF8'}40`, background: 'rgba(15, 23, 42, 0.85)' }}>
            <h3 className="section-card-title">
              <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <ShieldAlert size={16} color={cellRisk.risk_color || '#38BDF8'} />
                Dynamic Multi-Trigger Risk Score
              </span>
              <span className="section-status-tag" style={{ background: `${cellRisk.risk_color || '#38BDF8'}20`, color: cellRisk.risk_color || '#38BDF8', border: `1px solid ${cellRisk.risk_color || '#38BDF8'}40` }}>
                {cellRisk.risk_level ? `${cellRisk.risk_level.toUpperCase()} LEVEL` : cellRisk.risk_status}
              </span>
            </h3>

            <div className="metrics-grid">
              <div className="metric-box">
                <div className="metric-label">Combined Risk Score</div>
                <div className="metric-value highlight" style={{ color: cellRisk.risk_color || '#38BDF8' }}>
                  {cellRisk.combined_risk_score !== null ? `${cellRisk.combined_risk_score} / 100` : 'Unavailable'}
                </div>
              </div>

              <div className="metric-box">
                <div className="metric-label">Baseline Susceptibility</div>
                <div className="metric-value">
                  {cellRisk.baseline_susceptibility !== null ? `${cellRisk.baseline_susceptibility} (${cellRisk.baseline_class || 'TSI'})` : 'N/A'}
                </div>
              </div>

              <div className="metric-box">
                <div className="metric-label">Dynamic Trigger Score</div>
                <div className="metric-value" style={{ color: '#38BDF8' }}>
                  {cellRisk.dynamic_trigger_score !== null ? `${cellRisk.dynamic_trigger_score} / 100` : 'Suspended'}
                </div>
              </div>

              <div className="metric-box">
                <div className="metric-label">Data Completeness</div>
                <div className="metric-value">
                  {cellRisk.data_completeness !== null ? `${Math.round(cellRisk.data_completeness * 100)}%` : '0%'}
                </div>
              </div>

              {cellRisk.recommendation && (
                <div className="metric-box full-width-metric" style={{ background: 'rgba(56, 189, 248, 0.08)', padding: 8, borderRadius: 4, border: '1px solid rgba(56, 189, 248, 0.2)' }}>
                  <div style={{ fontSize: 11, color: '#F8FAFC', lineHeight: 1.4 }}>
                    <strong>Action Advisory:</strong> {cellRisk.recommendation}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Baseline Susceptibility Disclaimer */}
        <div className="scientific-disclaimer-box">
          <strong>Baseline Susceptibility Notice:</strong> Values represent prototype terrain-based susceptibility (TSI) derived from SRTM DEM 30m. Dynamic multi-source ML risk scores will be generated once live satellite and meteorological feeds are connected.
        </div>

        {/* Section 1: Terrain Morphometry */}
        <div className="section-card">
          <h3 className="section-card-title">
            <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <Mountain size={15} color="#00E599" />
              Terrain Morphometry (SRTM 30m)
            </span>
            <span className="section-status-tag available">Available</span>
          </h3>

          <div className="metrics-grid">
            <div className="metric-box">
              <div className="metric-label">Elevation (Mean)</div>
              <div className="metric-value">
                {elevation_m !== null ? `${elevation_m} m` : <span className="unavailable-text">NoData</span>}
              </div>
            </div>

            <div className="metric-box">
              <div className="metric-label">Elevation Range</div>
              <div className="metric-value">
                {elevation_min !== null && elevation_max !== null ? `${elevation_min}–${elevation_max} m` : <span className="unavailable-text">NoData</span>}
              </div>
            </div>

            <div className="metric-box">
              <div className="metric-label">Slope Gradient</div>
              <div className="metric-value highlight">
                {slope_deg !== null ? `${slope_deg}°` : <span className="unavailable-text">NoData</span>}
              </div>
            </div>

            <div className="metric-box">
              <div className="metric-label">Max Slope</div>
              <div className="metric-value">
                {slope_max_deg !== null ? `${slope_max_deg}°` : <span className="unavailable-text">NoData</span>}
              </div>
            </div>

            <div className="metric-box">
              <div className="metric-label">Aspect Orientation</div>
              <div className="metric-value">
                {aspect_deg !== null ? `${aspect_deg}°` : <span className="unavailable-text">NoData</span>}
              </div>
            </div>

            <div className="metric-box">
              <div className="metric-label">Profile Curvature</div>
              <div className="metric-value">
                {curvature !== null ? curvature : <span className="unavailable-text">NoData</span>}
              </div>
            </div>

            <div className="metric-box">
              <div className="metric-label">Topographic Wetness (TWI)</div>
              <div className="metric-value">
                {twi !== null ? twi : <span className="unavailable-text">NoData</span>}
              </div>
            </div>

            <div className="metric-box">
              <div className="metric-label">TSI Score</div>
              <div className="metric-value highlight">
                {tsi_score !== null ? `${tsi_score} / 100` : <span className="unavailable-text">NoData</span>}
              </div>
            </div>

            {primary_contributors && (
              <div className="metric-box full-width-metric">
                <div className="metric-label">Primary Susceptibility Drivers</div>
                <div className="metric-value" style={{ fontSize: 12, fontWeight: 500 }}>
                  {primary_contributors}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Section 2: Meteorological Precipitation */}
        <div className="section-card">
          <h3 className="section-card-title">
            <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <CloudRain size={15} color="#38BDF8" />
              Precipitation (NASA GPM IMERG)
            </span>
            {cellParameters?.rainfall?.status === 'AVAILABLE' ? (
              <span className="section-status-tag" style={{ background: 'rgba(52, 211, 153, 0.2)', color: '#34D399', border: '1px solid rgba(52, 211, 153, 0.4)' }}>
                AVAILABLE
              </span>
            ) : cellParameters?.rainfall?.status === 'STALE' ? (
              <span className="section-status-tag" style={{ background: 'rgba(234, 179, 8, 0.2)', color: '#FDE047', border: '1px solid rgba(234, 179, 8, 0.4)' }}>
                STALE
              </span>
            ) : (
              <span className="section-status-tag unavailable">UNAVAILABLE</span>
            )}
          </h3>

          <div className="metrics-grid">
            <div className="metric-box full-width-metric">
              <div className="metric-label">Data Status & Resolution</div>
              <div className="metric-value" style={{ fontSize: 11.5, color: cellParameters?.rainfall?.status === 'AVAILABLE' ? '#34D399' : '#94A3B8' }}>
                {cellParameters?.rainfall?.status === 'AVAILABLE'
                  ? `AVAILABLE — Real NASA GPM IMERG (${cellParameters.rainfall.source_resolution || '0.1° / ~10 km native resolution'})`
                  : unavailableNotice}
              </div>
            </div>

            <div className="metric-box">
              <div className="metric-label">Rainfall Rate</div>
              <div className="metric-value highlight" style={{ color: '#38BDF8' }}>
                {cellParameters?.rainfall?.rainfall_rate_mm_h !== null && cellParameters?.rainfall?.rainfall_rate_mm_h !== undefined
                  ? `${cellParameters.rainfall.rainfall_rate_mm_h} mm/h`
                  : <span className="unavailable-text">Unavailable</span>}
              </div>
            </div>

            <div className="metric-box">
              <div className="metric-label">24h Accumulation</div>
              <div className="metric-value">
                {cellParameters?.rainfall?.rainfall_24h_mm !== null && cellParameters?.rainfall?.rainfall_24h_mm !== undefined
                  ? `${cellParameters.rainfall.rainfall_24h_mm} mm`
                  : <span className="unavailable-text">N/A (partial window)</span>}
              </div>
            </div>

            <div className="metric-box">
              <div className="metric-label">72h Accumulation</div>
              <div className="metric-value">
                {cellParameters?.rainfall?.rainfall_72h_mm !== null && cellParameters?.rainfall?.rainfall_72h_mm !== undefined
                  ? `${cellParameters.rainfall.rainfall_72h_mm} mm`
                  : <span className="unavailable-text">N/A (partial window)</span>}
              </div>
            </div>

            <div className="metric-box">
              <div className="metric-label">Event Duration</div>
              <div className="metric-value">
                {cellParameters?.rainfall?.rainfall_duration_h !== null && cellParameters?.rainfall?.rainfall_duration_h !== undefined
                  ? `${cellParameters.rainfall.rainfall_duration_h} h`
                  : <span className="unavailable-text">0.0 h</span>}
              </div>
            </div>

            <div className="metric-box full-width-metric">
              <div className="metric-label">Observation Timestamp & Grid</div>
              <div className="metric-value" style={{ fontSize: 11, color: '#CBD5E1' }}>
                {cellParameters?.rainfall?.observation_timestamp
                  ? `${cellParameters.rainfall.observation_timestamp} (${cellParameters.rainfall.gpm_grid_cell || 'GPM_0.1DEG'})`
                  : 'N/A'}
              </div>
            </div>

            {cellParameters?.rainfall?.notice && (
              <div className="metric-box full-width-metric" style={{ background: 'rgba(56, 189, 248, 0.08)', padding: 8, borderRadius: 4, border: '1px solid rgba(56, 189, 248, 0.2)' }}>
                <div style={{ fontSize: 10.5, color: '#38BDF8', lineHeight: 1.35 }}>
                  <strong>Notice:</strong> {cellParameters.rainfall.notice}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Section 3: Soil Moisture */}
        <div className="section-card">
          <h3 className="section-card-title">
            <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <Droplets size={15} color="#60A5FA" />
              Soil Moisture (NASA SMAP 9km)
            </span>
            {smapData?.status === 'STALE' ? (
              <span className="section-status-tag" style={{ background: 'rgba(234, 179, 8, 0.2)', color: '#FDE047', border: '1px solid rgba(234, 179, 8, 0.4)' }}>
                STALE
              </span>
            ) : (
              <span className="section-status-tag unavailable">Pending Auth</span>
            )}
          </h3>

          <div className="metrics-grid">
            <div className="metric-box full-width-metric">
              <div className="metric-label">Data Status & Source</div>
              <div className="metric-value" style={{ fontSize: 11.5, color: smapData?.status === 'STALE' ? '#FDE047' : '#94A3B8' }}>
                {smapData?.status === 'STALE'
                  ? `STALE — Observation latency exceeded threshold (${smapData.source_product || 'SPL3SMP_E_V006'})`
                  : unavailableNotice}
              </div>
            </div>

            <div className="metric-box">
              <div className="metric-label">Volumetric Water (m³/m³)</div>
              <div className="metric-value highlight" style={{ color: '#60A5FA' }}>
                {smapData?.volumetric_moisture_m3_m3 !== null && smapData?.volumetric_moisture_m3_m3 !== undefined
                  ? `${smapData.volumetric_moisture_m3_m3} m³/m³`
                  : <span className="unavailable-text">Unavailable</span>}
              </div>
            </div>

            <div className="metric-box">
              <div className="metric-label">Moisture Differential</div>
              <div className="metric-value" style={{ fontSize: 12, color: smapData?.moisture_change_percent > 0 ? '#34D399' : '#E2E8F0' }}>
                {smapData?.moisture_change_percent !== null && smapData?.moisture_change_percent !== undefined
                  ? `+${smapData.moisture_change_percent}% (${smapData.moisture_change_m3_m3} m³/m³)`
                  : <span className="unavailable-text">Unavailable</span>}
              </div>
            </div>

            <div className="metric-box full-width-metric">
              <div className="metric-label">Observation Timestamp & Grid</div>
              <div className="metric-value" style={{ fontSize: 11, color: '#CBD5E1' }}>
                {smapData?.observation_timestamp
                  ? `${smapData.observation_timestamp} (${smapData.smap_ease2_grid_cell || 'EASE2_M09'})`
                  : 'N/A — pending NASA Earthdata login'}
              </div>
            </div>

            {smapData?.notice && (
              <div className="metric-box full-width-metric" style={{ background: 'rgba(234, 179, 8, 0.08)', padding: 8, borderRadius: 4, border: '1px solid rgba(234, 179, 8, 0.2)' }}>
                <div style={{ fontSize: 10.5, color: '#FDE047', lineHeight: 1.35 }}>
                  <strong>Notice:</strong> {smapData.notice}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Section 4: Sentinel-1 SAR Radar Evidence */}
        <div className="section-card">
          <h3 className="section-card-title">
            <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <Radio size={15} color="#A78BFA" />
              Satellite SAR Change (Sentinel-1)
            </span>
            <span className="section-status-tag unavailable">Pending Auth</span>
          </h3>

          <div className="metrics-grid">
            <div className="metric-box full-width-metric">
              <div className="metric-label">Status</div>
              <div className="metric-value unavailable-text">{unavailableNotice}</div>
            </div>
            <div className="metric-box">
              <div className="metric-label">VV Change (dB)</div>
              <div className="metric-value unavailable-text">Unavailable</div>
            </div>
            <div className="metric-box">
              <div className="metric-label">VH Change (dB)</div>
              <div className="metric-value unavailable-text">Unavailable</div>
            </div>
            <div className="metric-box">
              <div className="metric-label">Combined Δσ° (dB)</div>
              <div className="metric-value unavailable-text">Unavailable</div>
            </div>
            <div className="metric-box">
              <div className="metric-label">Anomaly Confidence</div>
              <div className="metric-value unavailable-text">Unavailable</div>
            </div>
            <div className="metric-box full-width-metric">
              <div className="metric-label">Corroborating Notice</div>
              <div style={{ fontSize: 11, color: '#94A3B8', lineHeight: 1.4 }}>
                SAR change is corroborating anomaly evidence only. It must never be automatically labelled as a landslide without ground or officer verification.
              </div>
            </div>
          </div>
        </div>

        {/* Section 5: Hydrological Flood Inundation */}
        <div className="section-card">
          <h3 className="section-card-title">
            <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <AlertCircle size={15} color="#F59E0B" />
              Hydrological Flood Hazard
            </span>
            <span className="section-status-tag unavailable">Not Connected</span>
          </h3>
          <div className="metric-box">
            <div className="metric-label">Status</div>
            <div className="metric-value unavailable-text">{unavailableNotice}</div>
          </div>
        </div>

        {/* Section 6: Verification & Ground Truth */}
        <div className="section-card">
          <h3 className="section-card-title">
            <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <ShieldAlert size={15} color="#34D399" />
              Field Inspection & Reports
            </span>
            <span className="section-status-tag available">Active</span>
          </h3>
          <div className="metrics-grid">
            <div className="metric-box">
              <div className="metric-label">Officer Verification</div>
              <div className="metric-value" style={{ fontSize: 12.5 }}>
                {has_verified_event ? 'VERIFIED INCIDENT' : 'Pending Field Report'}
              </div>
            </div>
            <div className="metric-box">
              <div className="metric-label">Citizen Reports</div>
              <div className="metric-value">0 filed</div>
            </div>
          </div>
        </div>

        {/* Section 7: Exposure & Critical Infrastructure */}
        <div className="section-card">
          <h3 className="section-card-title">
            <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <Users size={15} color="#EC4899" />
              Exposure & Infrastructure
            </span>
            <span className="section-status-tag unavailable">Pending Layer</span>
          </h3>
          <div className="metrics-grid">
            <div className="metric-box">
              <div className="metric-label">Road Proximity</div>
              <div className="metric-value unavailable-text">Unavailable</div>
            </div>
            <div className="metric-box">
              <div className="metric-label">Settlement Exposure</div>
              <div className="metric-value unavailable-text">Unavailable</div>
            </div>
            <div className="metric-box full-width-metric">
              <div className="metric-label">Critical Assets</div>
              <div className="metric-value unavailable-text">Unavailable — GIS layer pending integration</div>
            </div>
          </div>
        </div>
      </div>
    </aside>
  );
}
