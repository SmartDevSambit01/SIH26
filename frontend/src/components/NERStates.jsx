import React from 'react';

export default function NERStates() {
  const states = [
    'Arunachal Pradesh',
    'Assam',
    'Manipur',
    'Meghalaya',
    'Mizoram',
    'Nagaland',
    'Sikkim',
    'Tripura',
  ];

  return (
    <div className="ner-states-bar" aria-label="North Eastern Region States Covered">
      <div className="ner-states-container">
        {states.map((state, idx) => (
          <React.Fragment key={state}>
            <span className="ner-state-item">{state}</span>
            {idx < states.length - 1 && <span className="ner-state-separator">|</span>}
          </React.Fragment>
        ))}
      </div>
    </div>
  );
}
