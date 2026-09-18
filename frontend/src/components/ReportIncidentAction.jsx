import React from 'react';
import { Camera, Activity, Cpu, Users, Map } from 'lucide-react';

export default function ReportIncidentAction() {
  const handleReportClick = (e) => {
    e.preventDefault();
    alert('Incident reporting portal is ready for connection with the citizen reporting module.');
  };

  return (
    <div className="ner-hero-actions-container">
      {/* Report an incident button */}
      <button
        type="button"
        className="ner-report-incident-btn"
        onClick={handleReportClick}
      >
        <Camera className="ner-report-icon" size={18} />
        <span>Report an Incident</span>
      </button>

      {/* Feature tags strip shown in reference */}
      <div className="ner-feature-tags">
        <div className="ner-feature-tag">
          <span className="ner-tag-badge">8</span>
          <span>8 States</span>
        </div>
        <div className="ner-feature-divider" />
        <div className="ner-feature-tag">
          <Activity size={15} className="ner-tag-icon" />
          <span>Real-time Data</span>
        </div>
        <div className="ner-feature-divider" />
        <div className="ner-feature-tag">
          <Cpu size={15} className="ner-tag-icon" />
          <span>AI Prediction</span>
        </div>
        <div className="ner-feature-divider" />
        <div className="ner-feature-tag">
          <Users size={15} className="ner-tag-icon" />
          <span>Community Driven</span>
        </div>
      </div>
    </div>
  );
}
