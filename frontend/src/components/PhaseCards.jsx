import React from 'react';
import { MapPin, Bell, HeartHandshake } from 'lucide-react';

export default function PhaseCards({ onNavigate }) {
  const cards = [
    {
      id: 'pre',
      title: 'Pre-Landslide',
      subtext: 'Risk map monitoring',
      accentText: '(Preparation & Awareness)',
      icon: <MapPin className="ner-phase-icon" size={24} />,
      badgeClass: 'ner-phase-pre',
      action: () => onNavigate && onNavigate('RISK_MAP'),
    },
    {
      id: 'during',
      title: 'During-Landslide',
      subtext: 'Alarm Activated',
      accentText: '(Real-time Alert)',
      icon: <Bell className="ner-phase-icon" size={24} />,
      badgeClass: 'ner-phase-during',
    },
    {
      id: 'post',
      title: 'Post-Landslide',
      subtext: 'Recovery & Support',
      accentText: '(Community Help)',
      icon: <HeartHandshake className="ner-phase-icon" size={24} />,
      badgeClass: 'ner-phase-post',
    },
  ];

  return (
    <div className="ner-phase-cards-row">
      {cards.map((card) => (
        <div 
          key={card.id} 
          className={`ner-phase-card ${card.badgeClass}`}
          onClick={card.action}
          style={{ cursor: card.action ? 'pointer' : 'default' }}
        >
          <div className="ner-phase-icon-box">
            {card.icon}
          </div>
          <div className="ner-phase-info">
            <h3 className="ner-phase-title">{card.title}</h3>
            <p className="ner-phase-subtext">{card.subtext}</p>
          </div>
        </div>
      ))}
    </div>
  );
}
