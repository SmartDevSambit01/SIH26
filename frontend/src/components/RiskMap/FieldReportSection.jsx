import React, { useState, useEffect, useCallback } from 'react';
import { ShieldAlert, Send, CheckCircle2, Clock, XCircle } from 'lucide-react';

const REPORT_TYPES = [
  'GROUND_CRACK', 'ROAD_SETTLEMENT', 'ROCKFALL', 'MUD_MOVEMENT', 'WATER_SEEPAGE',
  'DRAINAGE_BLOCKAGE', 'FRESH_DEBRIS', 'FLOODED_ROAD', 'BRIDGE_OVERTOPPING', 'OTHER',
];

const STATUS_ICON = {
  VERIFIED: <CheckCircle2 size={12} color="#34D399" />,
  PENDING: <Clock size={12} color="#FBBF24" />,
  REJECTED: <XCircle size={12} color="#F87171" />,
};

const HOSTS = [import.meta.env.VITE_API_URL || '', 'http://127.0.0.1:8000', 'http://localhost:8000'];

async function tryHosts(path, options) {
  let lastErr;
  for (const host of HOSTS) {
    try {
      const res = await fetch(`${host}${path}`, options);
      if (res.ok) return res.json();
      lastErr = new Error(`HTTP ${res.status}`);
    } catch (err) {
      lastErr = err;
    }
  }
  throw lastErr;
}

export default function FieldReportSection({ cellId }) {
  const [reports, setReports] = useState(null);
  const [reportType, setReportType] = useState(REPORT_TYPES[0]);
  const [description, setDescription] = useState('');
  const [reporterRole, setReporterRole] = useState('CITIZEN');
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState(null);

  const loadReports = useCallback(async () => {
    if (!cellId) return;
    try {
      const data = await tryHosts(`/api/field-reports?cell_id=${cellId}`);
      setReports(data);
    } catch (err) {
      setReports([]);
    }
  }, [cellId]);

  useEffect(() => {
    loadReports();
  }, [loadReports]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!description.trim()) return;
    setSubmitting(true);
    setSubmitError(null);
    try {
      await tryHosts('/api/field-reports', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          cell_id: cellId,
          report_type: reportType,
          description: description.trim(),
          reporter_role: reporterRole,
        }),
      });
      setDescription('');
      await loadReports();
    } catch (err) {
      setSubmitError('Unable to submit report — backend unreachable.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="section-card">
      <h3 className="section-card-title">
        <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <ShieldAlert size={15} color="#34D399" />
          Field Inspection & Reports
        </span>
        <span className="section-status-tag available">Active</span>
      </h3>

      <div className="metrics-grid" style={{ marginBottom: 10 }}>
        <div className="metric-box">
          <div className="metric-label">Reports Filed</div>
          <div className="metric-value highlight">{reports === null ? '…' : reports.length}</div>
        </div>
        <div className="metric-box">
          <div className="metric-label">Verified</div>
          <div className="metric-value" style={{ color: '#34D399' }}>
            {reports === null ? '…' : reports.filter(r => r.verification_status === 'VERIFIED').length}
          </div>
        </div>
      </div>

      {reports && reports.length > 0 && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6, marginBottom: 10, maxHeight: 140, overflowY: 'auto' }}>
          {reports.map((r) => (
            <div key={r.report_id} style={{
              display: 'flex', alignItems: 'flex-start', gap: 6, fontSize: 11,
              padding: '6px 8px', background: 'rgba(255,255,255,0.03)', borderRadius: 4,
            }}>
              {STATUS_ICON[r.verification_status]}
              <div style={{ flex: 1 }}>
                <div style={{ color: '#E2E8F0', fontWeight: 600 }}>
                  {r.report_type.replace(/_/g, ' ')} <span style={{ color: '#64748B', fontWeight: 400 }}>({r.reporter_role})</span>
                </div>
                <div style={{ color: '#94A3B8' }}>{r.description}</div>
              </div>
            </div>
          ))}
        </div>
      )}

      <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
        <div style={{ display: 'flex', gap: 6 }}>
          <select
            value={reportType}
            onChange={(e) => setReportType(e.target.value)}
            style={{ flex: 1, fontSize: 11, background: 'rgba(15,23,42,0.8)', color: '#E2E8F0', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 4, padding: '4px 6px' }}
          >
            {REPORT_TYPES.map(t => <option key={t} value={t}>{t.replace(/_/g, ' ')}</option>)}
          </select>
          <select
            value={reporterRole}
            onChange={(e) => setReporterRole(e.target.value)}
            style={{ fontSize: 11, background: 'rgba(15,23,42,0.8)', color: '#E2E8F0', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 4, padding: '4px 6px' }}
          >
            <option value="CITIZEN">Citizen</option>
            <option value="FIELD_OFFICER">Field Officer</option>
            <option value="DISTRICT_ADMIN">District Admin</option>
          </select>
        </div>
        <textarea
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="Describe what you observed (e.g. fresh crack along the road shoulder)…"
          rows={2}
          style={{ fontSize: 11, background: 'rgba(15,23,42,0.8)', color: '#E2E8F0', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 4, padding: '6px 8px', resize: 'vertical' }}
        />
        <button
          type="submit"
          disabled={submitting || !description.trim()}
          style={{
            display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6,
            fontSize: 11, fontWeight: 600, padding: '6px', borderRadius: 4, border: 'none',
            background: submitting ? 'rgba(52,211,153,0.3)' : '#10B981', color: '#052e1a', cursor: submitting ? 'default' : 'pointer',
          }}
        >
          <Send size={12} />
          {submitting ? 'Submitting…' : 'Submit Field Report'}
        </button>
        {submitError && <div style={{ fontSize: 10.5, color: '#F87171' }}>{submitError}</div>}
      </form>
    </div>
  );
}
