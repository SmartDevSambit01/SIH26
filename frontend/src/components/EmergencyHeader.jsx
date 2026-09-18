import React from 'react';
import { AlertCircle } from 'lucide-react';

export default function EmergencyHeader() {
  return (
    <div className="ner-emergency-header-box">
      <div className="ner-emergency-header-icon-circle">
        <AlertCircle size={22} color="#ffffff" strokeWidth={2.4} />
      </div>
      <div className="ner-emergency-header-text">
        <h2 className="ner-emergency-header-title">Emergency Help</h2>
        <p className="ner-emergency-header-subtitle">
          (In case of immediate danger,call now)
        </p>
      </div>
    </div>
  );
}
