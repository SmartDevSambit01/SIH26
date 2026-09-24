import React, { useState } from 'react';
import { Cpu, ChevronDown, ChevronUp, ShieldAlert } from 'lucide-react';

export default function AiRiskEngineCard() {
  const [collapsed, setCollapsed] = useState(false);

  return (
    <div className="ai-risk-engine-card">
      <div 
        className="card-header" 
        onClick={() => setCollapsed(!collapsed)} 
        style={{ cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <Cpu size={14} color="#38BDF8" />
          <span style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.5px', color: '#E2E8F0', textTransform: 'uppercase' }}>
            AI-Assisted Risk Engine
          </span>
        </div>
        {collapsed ? <ChevronUp size={14} color="#94A3B8" /> : <ChevronDown size={14} color="#94A3B8" />}
      </div>

      {!collapsed && (
        <div style={{ marginTop: 10, display: 'flex', flexDirection: 'column', gap: 5 }}>
          {/* Step 1: Inputs */}
          <div className="flow-step-box">
            <span style={{ color: '#00E599', fontWeight: 600 }}>Terrain Morphometry</span>
            <span style={{ color: '#94A3B8', margin: '0 4px' }}>+</span>
            <span style={{ color: '#F472B6', fontWeight: 600 }}>Historical Evidence</span>
          </div>

          <div style={{ textAlign: 'center', lineHeight: 1, color: '#38BDF8', fontSize: 11, margin: '-2px 0' }}>↓</div>

          {/* Step 2: Baseline TSI */}
          <div className="flow-step-box">
            <span style={{ color: '#CBD5E1', fontWeight: 600 }}>Baseline Susceptibility (TSI)</span>
          </div>

          <div style={{ textAlign: 'center', lineHeight: 1, color: '#38BDF8', fontSize: 11, margin: '-2px 0' }}>+</div>

          {/* Step 3: Dynamic Triggers */}
          <div className="flow-step-box" style={{ background: 'rgba(56, 189, 248, 0.08)', borderColor: 'rgba(56, 189, 248, 0.3)' }}>
            <div style={{ color: '#38BDF8', fontWeight: 600, fontSize: 11 }}>Dynamic Environmental Triggers</div>
            <div style={{ color: '#94A3B8', fontSize: 10, marginTop: 2 }}>
              GPM Rainfall + SMAP Soil Moisture
            </div>
          </div>

          <div style={{ textAlign: 'center', lineHeight: 1, color: '#38BDF8', fontSize: 11, margin: '-2px 0' }}>↓</div>

          {/* Step 4: Cell-Level Risk Score */}
          <div className="flow-step-box">
            <span style={{ color: '#FBBF24', fontWeight: 600 }}>Cell-Level Risk Score</span>
          </div>

          <div style={{ textAlign: 'center', lineHeight: 1, color: '#38BDF8', fontSize: 11, margin: '-2px 0' }}>↓</div>

          {/* Step 5: Output */}
          <div className="flow-step-box" style={{ background: 'rgba(239, 68, 68, 0.1)', borderColor: 'rgba(239, 68, 68, 0.3)' }}>
            <span style={{ color: '#F87171', fontWeight: 700 }}>Risk Class + Recommended Action</span>
          </div>

          {/* Disclosure Badge */}
          <div className="ai-disclosure-badge">
            <ShieldAlert size={12} color="#F59E0B" style={{ flexShrink: 0 }} />
            <span>Prototype risk score — not a calibrated probability</span>
          </div>
        </div>
      )}
    </div>
  );
}
