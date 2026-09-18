import React from 'react';
import { Shield, Cross, AlertTriangle } from 'lucide-react';

export default function EmergencyServiceButtons() {
  const services = [
    {
      id: 'police',
      name: 'Police',
      number: '100',
      icon: <Shield size={20} color="#ffffff" strokeWidth={2.2} />,
      bgClass: 'ner-service-police',
      tel: '100',
    },
    {
      id: 'ambulance',
      name: 'Ambulance',
      number: '108',
      icon: <Cross size={20} color="#ffffff" strokeWidth={2.2} />,
      bgClass: 'ner-service-ambulance',
      tel: '108',
    },
    {
      id: 'disaster',
      name: 'Disaster Mgmt.',
      number: '1070',
      icon: <AlertTriangle size={20} color="#ffffff" strokeWidth={2.2} />,
      bgClass: 'ner-service-disaster',
      tel: '1070',
    },
  ];

  return (
    <div className="ner-emergency-services-row">
      {services.map((service) => (
        <a
          key={service.id}
          href={`tel:${service.tel}`}
          className={`ner-emergency-service-btn ${service.bgClass}`}
          aria-label={`Call ${service.name} at ${service.number}`}
        >
          <div className="ner-service-icon-wrap">
            {service.icon}
          </div>
          <span className="ner-service-name">{service.name}</span>
          <span className="ner-service-num">{service.number}</span>
        </a>
      ))}
    </div>
  );
}
