import React from 'react';
import Header from './Header';
import MottoPill from './MottoPill';
import RiskSearchCard from './RiskSearchCard';
import PhaseCards from './PhaseCards';
import EmergencyPanel from './EmergencyPanel';
import NERStates from './NERStates';
import '../LandingPage.css';

export default function LandingPage({ onNavigate }) {
  return (
    <div className="ner-landing-root">
      <Header onNavigate={onNavigate} activeNav="HOME" />

      <main className="ner-main">
        {/* Centered hero copy */}
        <section className="ner-hero-copy">
          <div className="ner-motto-wrapper">
            <MottoPill />
          </div>

          <h1 className="ner-hero-heading">
            AI-powered early warning &amp; landslide risk monitoring for the
            North Eastern Region
          </h1>

          <RiskSearchCard onNavigate={onNavigate} />
        </section>

        {/* Two-card hero media: mountain photo + emergency console */}
        <section className="ner-hero-media">
          <div className="ner-hero-photo-card">
            <div className="ner-hero-photo-overlay" />
          </div>
          <EmergencyPanel />
        </section>

        {/* Pre / During / Post phase strip */}
        <section className="ner-phase-section">
          <PhaseCards onNavigate={onNavigate} />
        </section>
      </main>

      <NERStates />
    </div>
  );
}
