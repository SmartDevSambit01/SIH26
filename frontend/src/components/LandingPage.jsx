import React from 'react';
import Header from './Header';
import HeroSection from './HeroSection';
import EmergencyPanel from './EmergencyPanel';
import NERStates from './NERStates';
import '../LandingPage.css';

export default function LandingPage({ onNavigate }) {
  return (
    <div className="ner-landing-root">
      {/* Background Mountain Image Overlay */}
      <div className="ner-bg-mountain" />
      <div className="ner-bg-vignette" />

      {/* Main Page Layout */}
      <div className="ner-page-content">
        {/* Top Navigation */}
        <Header onNavigate={onNavigate} activeNav="HOME" />

        {/* Central Operational Viewport */}
        <main className="ner-main-viewport">
          <div className="ner-main-container">
            {/* Left Hero & Predictive Operations */}
            <HeroSection onNavigate={onNavigate} />

            {/* Right Emergency & Quick Help Panel */}
            <EmergencyPanel />
          </div>
        </main>

        {/* Bottom Northeast States Footer Strip */}
        <NERStates />
      </div>
    </div>
  );
}
