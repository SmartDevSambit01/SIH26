import React from 'react';
import { PhoneCall } from 'lucide-react';

export default function Emergency112() {
  return (
    <a href="tel:112" className="ner-emergency-112-container" aria-label="Call emergency number 112">
      <div className="ner-phone-icon-circle">
        <PhoneCall size={34} color="#D02127" strokeWidth={2.4} />
      </div>
      <div className="ner-112-text-group">
        <span className="ner-112-number">112</span>
        <div className="ner-112-labels">
          <span className="ner-112-label-primary">Emergency Number</span>
          <span className="ner-112-label-secondary">(India)</span>
        </div>
      </div>
    </a>
  );
}
