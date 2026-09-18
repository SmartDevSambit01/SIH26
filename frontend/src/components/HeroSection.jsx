import React from 'react';
import MottoPill from './MottoPill';
import PhaseCards from './PhaseCards';
import RiskSearchCard from './RiskSearchCard';
import ReportIncidentAction from './ReportIncidentAction';

export default function HeroSection({ onNavigate }) {
  return (
    <section className="ner-hero-section">
      <div className="ner-hero-panel">
        {/* Main H1 Heading */}
        <h1 className="ner-hero-heading">
          AI-Powered Early Warning &amp; <br className="ner-heading-break" />
          Landslide Risk Monitoring System <br className="ner-heading-break" />
          for North Eastern Region
        </h1>

        {/* Motto Pill */}
        <div className="ner-motto-wrapper">
          <MottoPill />
        </div>

        {/* 3 Phase Cards: Pre, During, Post */}
        <PhaseCards onNavigate={onNavigate} />

        {/* Risk Search Box */}
        <RiskSearchCard onNavigate={onNavigate} />

        {/* Report an incident & tags */}
        <ReportIncidentAction />
      </div>
    </section>
  );
}
