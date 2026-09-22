/**
 * AlertPanel.jsx — Multi-Level Early Warning & Alert Dashboard (Task 10 Frontend)
 *
 * Connects to the backend /api/alerts endpoints to display:
 * - Active operational early-warning alerts (ADVISORY, WATCH, WARNING, EVACUATION)
 * - Alert lifecycle state (PENDING_VERIFICATION → DISPATCHED → ACKNOWLEDGED → EXPIRED)
 * - Officer verification workflow controls (APPROVE / REJECT / EMERGENCY_OVERRIDE)
 * - OASIS CAP v1.2 envelope details
 * - Telecom gateway integration status
 * - Recipient group templates (District, SDMA/NDMA, Local Community)
 * - Scenario Test: Generate a test alert via dynamic_overrides fixtures
 *
 * Data principle: The panel ONLY shows real alerts from the backend.
 * No fake alerts or probabilities are displayed.
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  AlertTriangle, Bell, Shield, CheckCircle, XCircle,
  Clock, Zap, ChevronDown, ChevronUp, RefreshCw, Radio,
  MapPin, Users, Building2, FileText, Activity,
} from 'lucide-react';

const API_BASE = 'http://localhost:8000';

// Alert level visual config
const LEVEL_CONFIG = {
  EVACUATION: {
    color: '#EF4444',
    bg: 'rgba(239, 68, 68, 0.12)',
    border: 'rgba(239, 68, 68, 0.45)',
    pulse: true,
    label: 'EVACUATION',
    icon: <AlertTriangle size={14} />,
  },
  WARNING: {
    color: '#F97316',
    bg: 'rgba(249, 115, 22, 0.12)',
    border: 'rgba(249, 115, 22, 0.40)',
    pulse: true,
    label: 'WARNING',
    icon: <Bell size={14} />,
  },
  WATCH: {
    color: '#EAB308',
    bg: 'rgba(234, 179, 8, 0.10)',
    border: 'rgba(234, 179, 8, 0.35)',
    pulse: false,
    label: 'WATCH',
    icon: <Shield size={14} />,
  },
  ADVISORY: {
    color: '#38BDF8',
    bg: 'rgba(56, 189, 248, 0.08)',
    border: 'rgba(56, 189, 248, 0.30)',
    pulse: false,
    label: 'ADVISORY',
    icon: <Radio size={14} />,
  },
};

const STATE_CONFIG = {
  PENDING_VERIFICATION: { color: '#FACC15', label: 'Awaiting Verification' },
  APPROVED: { color: '#22C55E', label: 'Approved' },
  DISPATCHED: { color: '#34D399', label: 'Dispatched' },
  ACKNOWLEDGED: { color: '#60A5FA', label: 'Acknowledged' },
  REJECTED: { color: '#94A3B8', label: 'Rejected' },
  EXPIRED: { color: '#475569', label: 'Expired' },
  GENERATED: { color: '#A78BFA', label: 'Generated' },
};

// Test fixture for scenario testing (does NOT modify real data)
const HIGH_RISK_DEMO_OVERRIDES = {
  rainfall: { rainfall_rate: 40.0, rainfall_24h: 130.0, rainfall_72h: 200.0 },
  soil_moisture: { soil_moisture_current: 0.46, soil_moisture_change_percent: 30.0 },
  flood: { flood_indicator: false },
  satellite: { vv_change_db: -4.5, vh_change_db: -4.0, change_confidence: 0.90 },
  verification: { officer_verification_status: 'REPORTED' },
};

// ─── Alert Card Component ──────────────────────────────────────────────────

function AlertCard({ alert, onRefresh }) {
  const [expanded, setExpanded] = useState(false);
  const [verifying, setVerifying] = useState(false);
  const [officerId, setOfficerId] = useState('DEMO_AUTHORIZED_OFFICER');
  const [officerRole, setOfficerRole] = useState('DISTRICT_DISASTER_MANAGEMENT_OFFICER');
  const [verifyNotes, setVerifyNotes] = useState('');
  const [actionLoading, setActionLoading] = useState(false);
  const [error, setError] = useState('');

  const level = LEVEL_CONFIG[alert.operational_alert_level] || LEVEL_CONFIG.ADVISORY;
  const state = STATE_CONFIG[alert.lifecycle_state] || { color: '#94A3B8', label: alert.lifecycle_state };

  const handleVerify = async (action) => {
    setActionLoading(true);
    setError('');
    try {
      const res = await fetch(`${API_BASE}/api/alerts/${alert.alert_id}/verify`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          action,
          officer_id: officerId,
          officer_role: officerRole,
          notes: verifyNotes || undefined,
        }),
      });
      if (!res.ok) {
        const err = await res.json();
        setError(err.detail || 'Verification failed.');
      } else {
        onRefresh();
        setVerifying(false);
      }
    } catch (e) {
      setError('Network error reaching backend.');
    } finally {
      setActionLoading(false);
    }
  };

  const handleAcknowledge = async () => {
    setActionLoading(true);
    setError('');
    try {
      const res = await fetch(`${API_BASE}/api/alerts/${alert.alert_id}/acknowledge`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          officer_id: officerId,
          agency: 'DISTRICT_EOC',
          notes: verifyNotes || undefined,
        }),
      });
      if (!res.ok) {
        const err = await res.json();
        setError(err.detail || 'Acknowledgement failed.');
      } else {
        onRefresh();
      }
    } catch (e) {
      setError('Network error reaching backend.');
    } finally {
      setActionLoading(false);
    }
  };

  return (
    <div
      id={`alert-card-${alert.alert_id}`}
      style={{
        background: level.bg,
        border: `1px solid ${level.border}`,
        borderRadius: 'var(--r-md)',
        marginBottom: 14,
        overflow: 'hidden',
        transition: 'all 0.25s ease',
      }}
    >
      {/* Alert Header */}
      <div
        onClick={() => setExpanded(!expanded)}
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 12,
          padding: '12px 16px',
          cursor: 'pointer',
        }}
      >
        {/* Level Badge */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 5,
            background: level.color + '22',
            border: `1px solid ${level.color}55`,
            borderRadius: 'var(--r-sm)',
            padding: '3px 8px',
            color: level.color,
            fontSize: 11,
            fontWeight: 700,
            letterSpacing: '0.06em',
            whiteSpace: 'nowrap',
          }}
        >
          {level.icon}
          {level.label}
        </div>

        {/* Alert ID & District */}
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ color: '#F1F5F9', fontSize: 12, fontWeight: 600, fontFamily: 'monospace', marginBottom: 2 }}>
            {alert.alert_id}
          </div>
          <div style={{ color: '#94A3B8', fontSize: 11, display: 'flex', gap: 8, alignItems: 'center' }}>
            <MapPin size={10} />
            {alert.district}
            <span style={{ color: '#475569' }}>•</span>
            Risk: {alert.risk_score?.toFixed(1) ?? 'N/A'}
          </div>
        </div>

        {/* Lifecycle State */}
        <div
          style={{
            fontSize: 10,
            color: state.color,
            fontWeight: 600,
            whiteSpace: 'nowrap',
            textAlign: 'right',
          }}
        >
          {state.label}
        </div>

        {expanded ? <ChevronUp size={14} color="#64748B" /> : <ChevronDown size={14} color="#64748B" />}
      </div>

      {/* Expanded Detail */}
      {expanded && (
        <div style={{ padding: '0 16px 16px', borderTop: '1px solid var(--c-hairline-soft)' }}>
          {/* Recipient Templates */}
          <div style={{ marginTop: 12, marginBottom: 12 }}>
            <div style={{ color: '#64748B', fontSize: 10, fontWeight: 700, marginBottom: 8, letterSpacing: '0.08em' }}>
              RECIPIENT DIRECTIVES
            </div>
            {Object.entries(alert.templates || {}).map(([group, tmpl]) => (
              <div
                key={group}
                style={{
                  background: 'rgba(255,255,255,0.04)',
                  borderRadius: 'var(--r-sm)',
                  padding: '8px 12px',
                  marginBottom: 6,
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4 }}>
                  {group === 'DISTRICT_AUTHORITY' && <Building2 size={11} color="#38BDF8" />}
                  {group === 'DISASTER_MANAGEMENT_AUTHORITY' && <Shield size={11} color="#A78BFA" />}
                  {group === 'LOCAL_COMMUNITY' && <Users size={11} color="#34D399" />}
                  <span style={{ fontSize: 10, fontWeight: 700, color: '#94A3B8', letterSpacing: '0.06em' }}>
                    {group.replace(/_/g, ' ')}
                  </span>
                </div>
                <div style={{ fontSize: 11, color: '#CBD5E1', lineHeight: 1.5 }}>
                  {tmpl.instruction}
                </div>
                <div style={{ marginTop: 4, fontSize: 10, fontWeight: 700, color: '#FACC15' }}>
                  → {tmpl.recommended_action}
                </div>
              </div>
            ))}
          </div>

          {/* Audit Trail */}
          <div style={{ marginBottom: 12 }}>
            <div style={{ color: '#64748B', fontSize: 10, fontWeight: 700, marginBottom: 8, letterSpacing: '0.08em' }}>
              AUDIT TRAIL ({alert.audit_trail?.length ?? 0} entries)
            </div>
            {(alert.audit_trail || []).map((entry, i) => (
              <div
                key={i}
                style={{
                  display: 'flex',
                  gap: 10,
                  marginBottom: 4,
                  fontSize: 10,
                  color: '#94A3B8',
                }}
              >
                <span style={{ color: '#475569', whiteSpace: 'nowrap' }}>
                  {entry.timestamp?.slice(11, 19)}Z
                </span>
                <span style={{ fontWeight: 700, color: '#E2E8F0' }}>{entry.action}</span>
                <span style={{ color: '#64748B' }}>by {entry.actor}</span>
                {entry.notes && (
                  <span style={{ color: '#475569', fontStyle: 'italic', flex: 1 }}>
                    — {entry.notes.slice(0, 80)}
                  </span>
                )}
              </div>
            ))}
          </div>

          {/* CAP Identifier */}
          {alert.cap_representation && (
            <div style={{
              background: 'rgba(167, 139, 250, 0.06)',
              border: '1px solid rgba(167, 139, 250, 0.18)',
              borderRadius: 'var(--r-sm)',
              padding: '8px 12px',
              marginBottom: 12,
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4 }}>
                <FileText size={11} color="#A78BFA" />
                <span style={{ fontSize: 10, fontWeight: 700, color: '#A78BFA', letterSpacing: '0.06em' }}>
                  OASIS CAP v1.2 PAYLOAD
                </span>
              </div>
              <div style={{ fontSize: 10, color: '#94A3B8', fontFamily: 'monospace' }}>
                ID: {alert.cap_representation.identifier}<br />
                Urgency: {alert.cap_representation.info?.urgency} •
                Severity: {alert.cap_representation.info?.severity} •
                Status: {alert.cap_representation.status}
              </div>
            </div>
          )}

          {/* Verification Controls */}
          {alert.lifecycle_state === 'PENDING_VERIFICATION' && (
            <div style={{
              background: 'rgba(250, 204, 21, 0.06)',
              border: '1px solid rgba(250, 204, 21, 0.25)',
              borderRadius: 'var(--r-md)',
              padding: '12px',
            }}>
              <div style={{ color: '#FACC15', fontSize: 11, fontWeight: 700, marginBottom: 8 }}>
                ⚠ REQUIRES AUTHORIZED OFFICER VERIFICATION
              </div>
              {!verifying ? (
                <button
                  id={`btn-verify-${alert.alert_id}`}
                  onClick={() => setVerifying(true)}
                  style={{
                    background: 'rgba(250,204,21,0.15)',
                    border: '1px solid rgba(250,204,21,0.35)',
                    borderRadius: 'var(--r-sm)',
                    color: '#FACC15',
                    fontSize: 11,
                    fontWeight: 600,
                    padding: '6px 14px',
                    cursor: 'pointer',
                  }}
                >
                  Officer Verification Panel
                </button>
              ) : (
                <div>
                  <input
                    id={`input-officer-id-${alert.alert_id}`}
                    placeholder="Officer ID"
                    value={officerId}
                    onChange={e => setOfficerId(e.target.value)}
                    style={inputStyle}
                  />
                  <input
                    id={`input-officer-role-${alert.alert_id}`}
                    placeholder="Officer Role"
                    value={officerRole}
                    onChange={e => setOfficerRole(e.target.value)}
                    style={{ ...inputStyle, marginTop: 6 }}
                  />
                  <textarea
                    id={`input-notes-${alert.alert_id}`}
                    placeholder="Verification notes (optional)"
                    value={verifyNotes}
                    onChange={e => setVerifyNotes(e.target.value)}
                    rows={2}
                    style={{ ...inputStyle, marginTop: 6, resize: 'vertical' }}
                  />
                  <div style={{ display: 'flex', gap: 8, marginTop: 10, flexWrap: 'wrap' }}>
                    <ActionButton
                      id={`btn-approve-${alert.alert_id}`}
                      label="✓ APPROVE"
                      color="#22C55E"
                      loading={actionLoading}
                      onClick={() => handleVerify('APPROVE')}
                    />
                    <ActionButton
                      id={`btn-reject-${alert.alert_id}`}
                      label="✗ REJECT"
                      color="#94A3B8"
                      loading={actionLoading}
                      onClick={() => handleVerify('REJECT')}
                    />
                    <ActionButton
                      id={`btn-emergency-${alert.alert_id}`}
                      label="⚡ EMERGENCY OVERRIDE"
                      color="#EF4444"
                      loading={actionLoading}
                      onClick={() => handleVerify('EMERGENCY_OVERRIDE')}
                    />
                  </div>
                  {error && <div style={{ marginTop: 8, color: '#EF4444', fontSize: 11 }}>{error}</div>}
                </div>
              )}
            </div>
          )}

          {/* Acknowledge Controls */}
          {alert.lifecycle_state === 'DISPATCHED' && (
            <div style={{
              background: 'rgba(52, 211, 153, 0.06)',
              border: '1px solid rgba(52, 211, 153, 0.25)',
              borderRadius: 'var(--r-md)',
              padding: '12px',
            }}>
              <div style={{ color: '#34D399', fontSize: 11, fontWeight: 700, marginBottom: 8 }}>
                Alert DISPATCHED — Awaiting Agency Acknowledgement
              </div>
              <button
                id={`btn-ack-${alert.alert_id}`}
                onClick={handleAcknowledge}
                disabled={actionLoading}
                style={{
                  background: 'rgba(52,211,153,0.15)',
                  border: '1px solid rgba(52,211,153,0.35)',
                  borderRadius: 'var(--r-sm)',
                  color: '#34D399',
                  fontSize: 11,
                  fontWeight: 600,
                  padding: '6px 14px',
                  cursor: actionLoading ? 'wait' : 'pointer',
                }}
              >
                {actionLoading ? 'Processing...' : '✓ Acknowledge Receipt'}
              </button>
              {error && <div style={{ marginTop: 8, color: '#EF4444', fontSize: 11 }}>{error}</div>}
            </div>
          )}

          {/* Transparency Notice */}
          <div style={{
            marginTop: 10,
            padding: '6px 10px',
            background: 'rgba(255,255,255,0.03)',
            borderRadius: 'var(--r-sm)',
            fontSize: 10,
            color: '#475569',
            lineHeight: 1.5,
          }}>
            {alert.notice}
          </div>
        </div>
      )}
    </div>
  );
}

function ActionButton({ id, label, color, loading, onClick }) {
  return (
    <button
      id={id}
      onClick={onClick}
      disabled={loading}
      style={{
        background: color + '18',
        border: `1px solid ${color}45`,
        borderRadius: 'var(--r-sm)',
        color,
        fontSize: 11,
        fontWeight: 700,
        padding: '6px 12px',
        cursor: loading ? 'wait' : 'pointer',
        transition: 'all 0.15s ease',
      }}
    >
      {loading ? '...' : label}
    </button>
  );
}

const inputStyle = {
  width: '100%',
  background: 'rgba(255,255,255,0.06)',
  border: '1px solid var(--c-hairline)',
  borderRadius: 'var(--r-sm)',
  color: '#E2E8F0',
  fontSize: 11,
  padding: '6px 10px',
  boxSizing: 'border-box',
  outline: 'none',
  fontFamily: 'inherit',
};

// ─── Main AlertPanel Component ─────────────────────────────────────────────

export default function AlertPanel({ district }) {
  const [alerts, setAlerts] = useState([]);
  const [gatewayStatus, setGatewayStatus] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [generating, setGenerating] = useState(false);
  const [genCellId, setGenCellId] = useState('');
  const [genError, setGenError] = useState('');
  const [genSuccess, setGenSuccess] = useState('');
  const [filterState, setFilterState] = useState('');

  const fetchAlerts = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const params = new URLSearchParams();
      if (district) params.set('district', district);
      if (filterState) params.set('state', filterState);
      const res = await fetch(`${API_BASE}/api/alerts?${params}`);
      if (!res.ok) throw new Error(`API returned ${res.status}`);
      const data = await res.json();
      setAlerts(data.alerts || []);
    } catch (e) {
      setError('Backend unreachable. Start the FastAPI server to load live alert data.');
      setAlerts([]);
    } finally {
      setLoading(false);
    }
  }, [district, filterState]);

  const fetchGatewayStatus = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/alerts/gateway/status`);
      if (res.ok) setGatewayStatus(await res.json());
    } catch {}
  }, []);

  useEffect(() => {
    fetchAlerts();
    fetchGatewayStatus();
    const iv = setInterval(() => fetchAlerts(), 30000);
    return () => clearInterval(iv);
  }, [fetchAlerts, fetchGatewayStatus]);

  const handleGenerateScenario = async () => {
    if (!genCellId.trim()) {
      setGenError('Enter a valid cell ID (e.g. KOH_01378 or AIZ_00100)');
      return;
    }
    setGenerating(true);
    setGenError('');
    setGenSuccess('');
    try {
      const res = await fetch(`${API_BASE}/api/alerts/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          cell_id: genCellId.trim().toUpperCase(),
          dynamic_overrides: HIGH_RISK_DEMO_OVERRIDES,
        }),
      });
      if (res.status === 201) {
        const alert = await res.json();
        setGenSuccess(`Candidate alert ${alert.alert_id} generated (${alert.operational_alert_level}). Awaiting verification.`);
        fetchAlerts();
      } else if (res.status === 204) {
        setGenError('No alert warranted: dynamic feeds unavailable or risk score below thresholds.');
      } else if (res.status === 404) {
        const d = await res.json();
        setGenError(d.detail || 'Cell not found.');
      } else {
        setGenError(`Unexpected response: ${res.status}`);
      }
    } catch {
      setGenError('Network error. Ensure the FastAPI backend is running.');
    } finally {
      setGenerating(false);
    }
  };

  const pendingCount = alerts.filter(a => a.lifecycle_state === 'PENDING_VERIFICATION').length;
  const dispatchedCount = alerts.filter(a => a.lifecycle_state === 'DISPATCHED').length;

  return (
    <div
      id="alert-panel"
      style={{
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
      }}
    >
      {/* Panel Header */}
      <div style={{
        padding: '14px 18px 12px',
        borderBottom: '1px solid var(--c-hairline-soft)',
        flexShrink: 0,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
          <Bell size={16} color="#EF4444" />
          <span style={{ color: '#F1F5F9', fontWeight: 700, fontSize: 14, letterSpacing: '0.02em', fontFamily: 'var(--font-display)' }}>
            Early Warning Alerts
          </span>
          <div style={{ flex: 1 }} />
          <button
            id="btn-refresh-alerts"
            onClick={fetchAlerts}
            disabled={loading}
            title="Refresh alerts"
            style={{
              background: 'none',
              border: 'none',
              cursor: loading ? 'wait' : 'pointer',
              color: '#64748B',
              padding: 4,
            }}
          >
            <RefreshCw size={14} className={loading ? 'spin' : ''} />
          </button>
        </div>

        {/* Summary Chips */}
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          <StatusChip
            label={`${alerts.length} Total`}
            color="#64748B"
          />
          {pendingCount > 0 && (
            <StatusChip label={`${pendingCount} Pending Review`} color="#FACC15" pulsing />
          )}
          {dispatchedCount > 0 && (
            <StatusChip label={`${dispatchedCount} Dispatched`} color="#34D399" />
          )}
        </div>
      </div>

      {/* Scrollable Content */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '14px 18px' }}>

        {/* Scenario Test Generator */}
        <div style={{
          background: 'rgba(255, 119, 89, 0.06)',
          border: '1px solid rgba(255, 119, 89, 0.20)',
          borderRadius: 'var(--r-md)',
          padding: '12px 14px',
          marginBottom: 16,
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
            <Zap size={13} color="var(--c-coral)" />
            <span style={{ color: 'var(--c-coral)', fontSize: 11, fontWeight: 700, letterSpacing: '0.06em' }}>
              SCENARIO TEST — GENERATE CANDIDATE ALERT
            </span>
          </div>
          <div style={{ fontSize: 10, color: '#64748B', marginBottom: 10, lineHeight: 1.5 }}>
            Simulates high-risk dynamic conditions (GPM rainfall + SMAP moisture) for a specific cell
            using test fixtures. Does NOT modify real production data.
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            <input
              id="input-gen-cell-id"
              type="text"
              placeholder="Cell ID (e.g. KOH_01378)"
              value={genCellId}
              onChange={e => setGenCellId(e.target.value)}
              style={{ ...inputStyle, flex: 1 }}
            />
            <button
              id="btn-generate-scenario"
              onClick={handleGenerateScenario}
              disabled={generating}
              style={{
                background: 'rgba(255,119,89,0.15)',
                border: '1px solid rgba(255,119,89,0.35)',
                borderRadius: 'var(--r-sm)',
                color: 'var(--c-coral)',
                fontSize: 11,
                fontWeight: 700,
                padding: '6px 14px',
                cursor: generating ? 'wait' : 'pointer',
                whiteSpace: 'nowrap',
              }}
            >
              {generating ? 'Evaluating...' : 'Generate Alert'}
            </button>
          </div>
          {genSuccess && (
            <div style={{ marginTop: 8, color: '#34D399', fontSize: 11 }}>✓ {genSuccess}</div>
          )}
          {genError && (
            <div style={{ marginTop: 8, color: '#EF4444', fontSize: 11 }}>✗ {genError}</div>
          )}
        </div>

        {/* State Filter */}
        <div style={{ display: 'flex', gap: 6, marginBottom: 14, flexWrap: 'wrap' }}>
          {['', 'PENDING_VERIFICATION', 'DISPATCHED', 'ACKNOWLEDGED', 'REJECTED', 'EXPIRED'].map(s => (
            <button
              key={s}
              id={`filter-state-${s || 'all'}`}
              onClick={() => setFilterState(s)}
              style={{
                background: filterState === s ? 'rgba(255,119,89,0.15)' : 'rgba(255,255,255,0.04)',
                border: filterState === s ? '1px solid rgba(255,119,89,0.40)' : '1px solid var(--c-hairline-soft)',
                borderRadius: 'var(--r-sm)',
                color: filterState === s ? 'var(--c-coral)' : '#64748B',
                fontSize: 10,
                fontWeight: 600,
                padding: '4px 10px',
                cursor: 'pointer',
              }}
            >
              {s || 'All States'}
            </button>
          ))}
        </div>

        {/* Error State */}
        {error && (
          <div style={{
            background: 'rgba(239,68,68,0.08)',
            border: '1px solid rgba(239,68,68,0.25)',
            borderRadius: 'var(--r-sm)',
            padding: '10px 14px',
            marginBottom: 12,
            color: '#FCA5A5',
            fontSize: 11,
          }}>
            {error}
          </div>
        )}

        {/* Alert List */}
        {!loading && alerts.length === 0 && !error && (
          <div style={{
            textAlign: 'center',
            padding: '30px 20px',
            color: '#475569',
            fontSize: 12,
          }}>
            <Activity size={28} color="#334155" style={{ marginBottom: 10 }} />
            <div style={{ fontWeight: 600, color: '#64748B' }}>No Active Alerts</div>
            <div style={{ marginTop: 6, fontSize: 11 }}>
              {filterState ? `No alerts in "${filterState}" state.` : 'All clear. Use the scenario generator above to test the alert workflow.'}
            </div>
          </div>
        )}

        {alerts.map(alert => (
          <AlertCard key={alert.alert_id} alert={alert} onRefresh={fetchAlerts} />
        ))}

        {/* Gateway Status */}
        {gatewayStatus && (
          <div style={{
            marginTop: 8,
            background: 'rgba(167, 139, 250, 0.05)',
            border: '1px solid rgba(167, 139, 250, 0.15)',
            borderRadius: 'var(--r-md)',
            padding: '12px 14px',
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 10 }}>
              <Radio size={13} color="#A78BFA" />
              <span style={{ color: '#A78BFA', fontSize: 11, fontWeight: 700, letterSpacing: '0.06em' }}>
                DISSEMINATION GATEWAY STATUS
              </span>
            </div>
            {Object.entries(gatewayStatus).map(([channel, info]) => (
              <div
                key={channel}
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  padding: '5px 0',
                  borderBottom: '1px solid var(--c-hairline-soft)',
                  fontSize: 10,
                }}
              >
                <span style={{ color: '#94A3B8', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
                  {channel.replace(/_/g, ' ')}
                </span>
                <span style={{
                  color: info.status === 'ACTIVE' ? '#22C55E' : '#64748B',
                  fontWeight: 600,
                }}>
                  {info.status}
                </span>
              </div>
            ))}
            <div style={{ marginTop: 8, fontSize: 10, color: '#475569', lineHeight: 1.5 }}>
              Cell Broadcast requires official telecom operator gateway sign-off.
              OASIS CAP v1.2 payload is integration-ready for NDMA SACHET API.
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function StatusChip({ label, color, pulsing }) {
  return (
    <span style={{
      display: 'inline-flex',
      alignItems: 'center',
      gap: 5,
      background: color + '15',
      border: `1px solid ${color}35`,
      borderRadius: 'var(--r-full)',
      padding: '2px 9px',
      fontSize: 10,
      color,
      fontWeight: 600,
    }}>
      {pulsing && (
        <span style={{
          width: 6,
          height: 6,
          borderRadius: '50%',
          background: color,
          display: 'inline-block',
          animation: 'pulseRing 1.5s ease-in-out infinite',
        }} />
      )}
      {label}
    </span>
  );
}
