import React from 'react';
import EmergencyHeader from './EmergencyHeader';
import Emergency112 from './Emergency112';
import EmergencyServiceButtons from './EmergencyServiceButtons';
import QuickAccess from './QuickAccess';
import SafetyStrip from './SafetyStrip';

export default function EmergencyPanel() {
  return (
    <aside className="ner-emergency-panel" aria-label="Emergency Help and Quick Services">
      <div className="ner-emergency-panel-glass">
        {/* Red emergency banner */}
        <EmergencyHeader />

        {/* 112 Primary Emergency Call Section */}
        <Emergency112 />

        {/* Quick action service buttons: Police, Ambulance, Disaster Mgmt. */}
        <EmergencyServiceButtons />

        {/* Divider */}
        <div className="ner-panel-divider" />

        {/* Quick Access: Hospitals, Police, Shelters */}
        <QuickAccess />

        {/* Bottom Safety Strip */}
        <SafetyStrip />
      </div>
    </aside>
  );
}
