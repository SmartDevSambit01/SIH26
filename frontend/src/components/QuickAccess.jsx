import React from 'react';
import { Building2, ShieldCheck, Home } from 'lucide-react';

export default function QuickAccess() {
  const facilities = [
    {
      id: 'hospitals',
      title: 'Hospitals',
      linkText: 'View List',
      icon: <Building2 size={24} color="#0A7D4C" strokeWidth={2} />,
      iconBg: 'ner-quick-icon-green',
    },
    {
      id: 'police',
      title: 'Police Stations',
      linkText: 'View List',
      icon: <ShieldCheck size={24} color="#0A72D0" strokeWidth={2} />,
      iconBg: 'ner-quick-icon-blue',
    },
    {
      id: 'shelters',
      title: 'Emergency Shelters',
      linkText: 'View List',
      icon: <Home size={24} color="#0A7D4C" strokeWidth={2} />,
      iconBg: 'ner-quick-icon-teal',
    },
  ];

  const handleLinkClick = (e, item) => {
    e.preventDefault();
    alert(`Opening directory for ${item.title}`);
  };

  return (
    <div className="ner-quick-access-section">
      <h3 className="ner-quick-access-title">Nearby Healthcare &amp; Police Stations</h3>
      <div className="ner-quick-access-row">
        {facilities.map((fac) => (
          <div key={fac.id} className="ner-quick-card">
            <div className={`ner-quick-icon-box ${fac.iconBg}`}>
              {fac.icon}
            </div>
            <div className="ner-quick-title">{fac.title}</div>
            <a
              href={`#${fac.id}`}
              onClick={(e) => handleLinkClick(e, fac)}
              className="ner-quick-link"
            >
              {fac.linkText}
            </a>
          </div>
        ))}
      </div>
    </div>
  );
}
