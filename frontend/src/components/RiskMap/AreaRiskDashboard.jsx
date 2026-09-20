import React, { useState, useEffect } from 'react';
import { X, ShieldAlert, AlertTriangle, Layers, Info, CheckCircle2, XCircle, Database, Cpu } from 'lucide-react';

export default function AreaRiskDashboard({ areaId, onClose, onSelectCell }) {
  const [areaDetail, setAreaDetail] = useState(null);
  const [riskSummary, setRiskSummary] = useState(null);
  const [cellsData, setCellsData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [aiExplanation, setAiExplanation] = useState(null);

  useEffect(() => {
    if (!areaId) return;
    loadAreaData(areaId);

    setAiExplanation(null);
    const hosts = [
      import.meta.env.VITE_API_URL || '',
      'http://127.0.0.1:8000',
      'http://localhost:8000'
    ];
    (async () => {
      for (const host of hosts) {
        try {
          const res = await fetch(`${host}/api/areas/${areaId}/ai-explanation`);
          if (res.ok) {
            setAiExplanation(await res.json());
            return;
          }
        } catch (err) { /* try next host */ }
      }
      setAiExplanation({ status: 'AI_UNAVAILABLE', notice: 'Unable to reach AI narrative service.' });
    })();
  }, [areaId]);

  const loadAreaData = async (aid) => {
    setIsLoading(true);
    setError(null);

    const hosts = [
      import.meta.env.VITE_API_URL || '',
      'http://127.0.0.1:8000',
      'http://localhost:8000'
    ];

    let successData = null;
    let lastErr = null;

    for (const host of hosts) {
      try {
        const [detailRes, riskRes, cellsRes] = await Promise.all([
          fetch(`${host}/api/areas/${aid}`),
          fetch(`${host}/api/areas/${aid}/risk`),
          fetch(`${host}/api/areas/${aid}/cells`)
        ]);

        if (detailRes.ok && riskRes.ok && cellsRes.ok) {
          const detail = await detailRes.json();
          const risk = await riskRes.json();
          const cells = await cellsRes.json();
          successData = { detail, risk, cells };
          break;
        }
      } catch (err) {
        lastErr = err;
      }
    }

    if (successData) {
      setAreaDetail(successData.detail);
      setRiskSummary(successData.risk);
      setCellsData(successData.cells);
      setIsLoading(false);
    } else {
      console.error('Error loading Area Intelligence Dashboard:', lastErr);
      setError('Unable to fetch area details.');
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

  if (isLoading) {
    return (
      <div className="area-risk-dashboard-drawer" style={{
        position: 'absolute', top: 0, right: 0, width: '420px', height: '100%',
        background: 'rgba(15, 23, 42, 0.98)', backdropFilter: 'blur(16px)',
        borderLeft: '1px solid rgba(255, 255, 255, 0.12)', zIndex: 950, padding: '24px',
        color: '#F8FAFC', display: 'flex', alignItems: 'center', justifyContent: 'center'
      }}>
        <div style={{ textAlign: 'center', color: '#38BDF8' }}>
          <Layers className="animate-spin" size={32} style={{ margin: '0 auto 12px' }} />
          <div>Loading Area Risk Dashboard...</div>
        </div>
      </div>
    );
  }

  if (error || !riskSummary) {
    return (
      <div className="area-risk-dashboard-drawer" style={{
        position: 'absolute', top: 0, right: 0, width: '420px', height: '100%',
        background: 'rgba(15, 23, 42, 0.98)', backdropFilter: 'blur(16px)',
        borderLeft: '1px solid rgba(255, 255, 255, 0.12)', zIndex: 950, padding: '24px',
        color: '#F8FAFC'
      }}>
        <button onClick={onClose} style={{ background: 'none', border: 'none', color: '#94A3B8', cursor: 'pointer', float: 'right' }}>
          <X size={20} />
        </button>
        <h3 style={{ color: '#EF4444', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <AlertTriangle size={20} />
          <span>Error</span>
        </h3>
        <p style={{ color: '#94A3B8', fontSize: '14px' }}>{error || 'Area data not found.'}</p>
      </div>
    );
  }

  return (
    <div className="area-risk-dashboard-drawer" style={{
      position: 'absolute', top: 0, right: 0, width: '440px', height: '100%',
      background: 'rgba(11, 17, 32, 0.97)', backdropFilter: 'blur(20px)',
      borderLeft: '1px solid rgba(56, 189, 248, 0.25)', zIndex: 950,
      display: 'flex', flexDirection: 'column', color: '#F8FAFC',
      boxShadow: '-8px 0 32px rgba(0,0,0,0.5)', overflowY: 'auto'
    }}>
      {/* Header */}
      <div style={{
        padding: '20px 24px', borderBottom: '1px solid rgba(255,255,255,0.08)',
        background: 'rgba(30, 41, 59, 0.5)', position: 'sticky', top: 0, zIndex: 10
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <div style={{ fontSize: '11px', fontWeight: 600, color: '#38BDF8', letterSpacing: '0.05em', textTransform: 'uppercase' }}>
              Area / Locality Risk Intelligence
            </div>
            <h2 style={{ margin: '4px 0 0', fontSize: '20px', fontWeight: 700, color: '#FFFFFF' }}>
              📍 {riskSummary.area_name}
            </h2>
          </div>
          <button
            onClick={onClose}
            style={{
              background: 'rgba(255,255,255,0.08)', border: 'none', borderRadius: '6px',
              color: '#94A3B8', cursor: 'pointer', padding: '6px'
            }}
            title="Return to District View"
          >
            <X size={18} />
          </button>
        </div>

        <div style={{ display: 'flex', gap: '12px', marginTop: '10px', fontSize: '12px', color: '#CBD5E1' }}>
          <span>District: <strong>{riskSummary.district}</strong></span>
          <span>•</span>
          <span>Type: <strong style={{ textTransform: 'capitalize' }}>{riskSummary.place_type}</strong></span>
          <span>•</span>
          <span>Source: <strong style={{ color: '#94A3B8' }}>OSM Overpass</strong></span>
        </div>
      </div>

      <div style={{ padding: '20px 24px', display: 'flex', flexDirection: 'column', gap: '20px' }}>

        {/* Warning Disclaimer */}
        <div style={{
          padding: '12px 14px', borderRadius: '8px', background: 'rgba(245, 158, 11, 0.10)',
          border: '1px solid rgba(245, 158, 11, 0.30)', color: '#FCD34D', fontSize: '12px',
          display: 'flex', alignItems: 'center', gap: '10px'
        }}>
          <Info size={18} style={{ flexShrink: 0 }} />
          <span>{riskSummary.notice}</span>
        </div>

        {/* Baseline Susceptibility Card */}
        <div style={{
          background: 'rgba(30, 41, 59, 0.6)', borderRadius: '12px', padding: '16px',
          border: '1px solid rgba(255, 255, 255, 0.10)'
        }}>
          <div style={{ fontSize: '12px', fontWeight: 600, color: '#94A3B8', textTransform: 'uppercase', marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '6px' }}>
            <ShieldAlert size={14} style={{ color: '#38BDF8' }} />
            <span>Baseline Susceptibility</span>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '12px', marginBottom: '16px' }}>
            <div style={{ background: 'rgba(15, 23, 42, 0.7)', padding: '10px', borderRadius: '8px', textAlign: 'center' }}>
              <div style={{ fontSize: '11px', color: '#94A3B8' }}>Dominant Class</div>
              <div style={{
                fontSize: '13px', fontWeight: 700, marginTop: '4px',
                color: getRiskBadgeColor(riskSummary.dominant_class)
              }}>
                {riskSummary.dominant_class || 'N/A'}
              </div>
            </div>

            <div style={{ background: 'rgba(15, 23, 42, 0.7)', padding: '10px', borderRadius: '8px', textAlign: 'center' }}>
              <div style={{ fontSize: '11px', color: '#94A3B8' }}>Maximum TSI</div>
              <div style={{ fontSize: '16px', fontWeight: 700, color: '#F8FAFC', marginTop: '2px' }}>
                {riskSummary.max_tsi !== null ? riskSummary.max_tsi : 'N/A'}
              </div>
            </div>

            <div style={{ background: 'rgba(15, 23, 42, 0.7)', padding: '10px', borderRadius: '8px', textAlign: 'center' }}>
              <div style={{ fontSize: '11px', color: '#94A3B8' }}>Total Cells</div>
              <div style={{ fontSize: '16px', fontWeight: 700, color: '#38BDF8', marginTop: '2px' }}>
                {riskSummary.cell_count}
              </div>
            </div>
          </div>

          {/* TSI Distribution Bar Breakdown */}
          {riskSummary.class_distribution && Object.keys(riskSummary.class_distribution).length > 0 && (
            <div>
              <div style={{ fontSize: '11px', color: '#CBD5E1', marginBottom: '6px' }}>
                Risk Class Distribution (% of associated cells):
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                {Object.entries(riskSummary.class_distribution).map(([cls, pct]) => (
                  <div key={cls} style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '11px' }}>
                    <span style={{ width: '75px', color: getRiskBadgeColor(cls), fontWeight: 600 }}>{cls}</span>
                    <div style={{ flex: 1, height: '6px', background: 'rgba(255,255,255,0.1)', borderRadius: '3px', overflow: 'hidden' }}>
                      <div style={{ width: `${pct}%`, height: '100%', background: getRiskBadgeColor(cls), borderRadius: '3px' }} />
                    </div>
                    <span style={{ width: '40px', textAlign: 'right', color: '#94A3B8' }}>{pct}%</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* AI Narrative Summary (LLM-generated, grounded only in the real data above) */}
        <div style={{
          background: 'rgba(56, 189, 248, 0.06)', borderRadius: '12px', padding: '16px',
          border: '1px solid rgba(56, 189, 248, 0.2)'
        }}>
          <div style={{ fontSize: '12px', fontWeight: 600, color: '#94A3B8', textTransform: 'uppercase', marginBottom: '10px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <Cpu size={14} style={{ color: '#38BDF8' }} />
              <span>AI Risk Narrative</span>
            </span>
            {aiExplanation?.recommended_action && (
              <span style={{
                fontSize: '10px', padding: '3px 8px', borderRadius: '4px',
                background: 'rgba(56, 189, 248, 0.2)', color: '#38BDF8', border: '1px solid rgba(56, 189, 248, 0.4)'
              }}>
                {aiExplanation.recommended_action.replace(/_/g, ' ')}
              </span>
            )}
          </div>

          {aiExplanation === null ? (
            <div style={{ fontSize: '12px', color: '#94A3B8' }}>Loading AI summary…</div>
          ) : aiExplanation.status === 'AVAILABLE' ? (
            <>
              <div style={{ fontSize: '13px', color: '#F1F5F9', lineHeight: 1.5 }}>
                {aiExplanation.explanation}
              </div>
              {aiExplanation.action_reason && (
                <div style={{ fontSize: '11px', color: '#94A3B8', marginTop: '8px', fontStyle: 'italic' }}>
                  {aiExplanation.action_reason}
                </div>
              )}
            </>
          ) : (
            <div style={{ fontSize: '12px', color: '#F59E0B' }}>
              {aiExplanation.notice || 'Unavailable — AI narrative service not reachable.'}
            </div>
          )}
        </div>

        {/* Historical Evidence Card */}
        <div style={{
          background: 'rgba(30, 41, 59, 0.6)', borderRadius: '12px', padding: '16px',
          border: '1px solid rgba(255, 255, 255, 0.10)'
        }}>
          <div style={{ fontSize: '12px', fontWeight: 600, color: '#94A3B8', textTransform: 'uppercase', marginBottom: '10px', display: 'flex', alignItems: 'center', gap: '6px' }}>
            <Database size={14} style={{ color: '#F59E0B' }} />
            <span>Historical Landslide Evidence</span>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '13px' }}>
            {riskSummary.has_historical_events ? (
              <>
                <CheckCircle2 size={16} style={{ color: '#EF4444' }} />
                <span style={{ color: '#F8FAFC', fontWeight: 600 }}>
                  Verified Historical Landslide Recorded
                </span>
              </>
            ) : (
              <>
                <XCircle size={16} style={{ color: '#10B981' }} />
                <span style={{ color: '#94A3B8' }}>
                  No verified historical landslide points in this area
                </span>
              </>
            )}
          </div>

          {riskSummary.historical_event_ids && riskSummary.historical_event_ids.length > 0 && (
            <div style={{ marginTop: '8px', fontSize: '12px', color: '#CBD5E1' }}>
              Verified Event IDs: {riskSummary.historical_event_ids.map(id => (
                <span key={id} style={{
                  padding: '2px 6px', background: 'rgba(239, 68, 68, 0.2)', border: '1px solid rgba(239, 68, 68, 0.4)',
                  borderRadius: '4px', color: '#FCA5A5', marginRight: '6px', fontSize: '11px', fontFamily: 'monospace'
                }}>
                  {id}
                </span>
              ))}
            </div>
          )}
        </div>

        {/* Associated 500m Analysis Cells */}
        <div style={{
          background: 'rgba(30, 41, 59, 0.6)', borderRadius: '12px', padding: '16px',
          border: '1px solid rgba(255, 255, 255, 0.10)'
        }}>
          <div style={{ fontSize: '12px', fontWeight: 600, color: '#94A3B8', textTransform: 'uppercase', marginBottom: '10px', display: 'flex', justifyContent: 'space-between' }}>
            <span>Associated 500m Grid Cells</span>
            <span style={{ color: '#38BDF8' }}>{cellsData?.total_cells || 0} Cells</span>
          </div>

          <div style={{ maxHeight: '160px', overflowY: 'auto', display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
            {cellsData?.cells.map(c => (
              <span
                key={c.cell_id}
                onClick={() => onSelectCell && onSelectCell(c.cell_id)}
                style={{
                  padding: '4px 8px', borderRadius: '4px', background: 'rgba(15, 23, 42, 0.8)',
                  border: `1px solid ${getRiskBadgeColor(c.tsi_class)}40`, color: '#F1F5F9',
                  fontSize: '11px', cursor: 'pointer', fontFamily: 'monospace'
                }}
                title={`Cell ${c.cell_id} | TSI: ${c.tsi_score} (${c.tsi_class}) | Elev: ${c.elevation_mean}m`}
              >
                {c.cell_id}
              </span>
            ))}
          </div>
        </div>

        {/* Dynamic Data Feeds Status (Truthful Non-Fabricated Status) */}
        <div style={{
          background: 'rgba(30, 41, 59, 0.6)', borderRadius: '12px', padding: '16px',
          border: '1px solid rgba(255, 255, 255, 0.10)'
        }}>
          <div style={{ fontSize: '12px', fontWeight: 600, color: '#94A3B8', textTransform: 'uppercase', marginBottom: '10px' }}>
            Dynamic Real-Time Sensors
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', fontSize: '12px' }}>
            {['rainfall', 'soil_moisture', 'sentinel1', 'flood'].map((key) => {
              const labels = { rainfall: 'GPM Rainfall', soil_moisture: 'SMAP Soil Moisture', sentinel1: 'Sentinel-1 SAR', flood: 'Flood Hydrodynamics' };
              const text = riskSummary.dynamic_status?.[key] || 'Status unavailable';
              const color = text.toUpperCase().startsWith('AVAILABLE') ? '#34D399' : text.toUpperCase().startsWith('STALE') ? '#FDE047' : '#F59E0B';
              return (
                <div key={key} style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0', borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                  <span style={{ color: '#CBD5E1' }}>{labels[key]}:</span>
                  <span style={{ color, fontSize: '11px', textAlign: 'right', maxWidth: '60%' }}>{text}</span>
                </div>
              );
            })}
          </div>
        </div>

      </div>
    </div>
  );
}
