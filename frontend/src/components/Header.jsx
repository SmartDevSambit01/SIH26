import React, { useState } from "react";
import { Menu, X } from "lucide-react";

export default function Header({
  onNavigate,
  activeNav: propActiveNav = "HOME",
}) {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [activeNav, setActiveNav] = useState(propActiveNav);

  const navItems = [
    { label: "HOME", id: "home" },
    { label: "ALERTS", id: "alerts" },
    { label: "RISK MAP", id: "risk-map" },
  ];

  const handleNavClick = (e, label) => {
    e.preventDefault();
    setActiveNav(label);
    if (onNavigate) {
      if (label === "RISK MAP") onNavigate("RISK_MAP");
      else if (label === "HOME") onNavigate("HOME");
      else if (label === "ALERTS") onNavigate("ALERTS");
    }
  };

  return (
    <header className="ner-header">
      <div className="ner-header-container">
        {/* Brand / Logo */}
        <div className="ner-brand">
          <div className="ner-logo-icon">
            <svg
              viewBox="0 0 48 36"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
            >
              {/* Modern geometric mountain icon matching NER Safe branding */}
              <path
                d="M14 32L24 10L34 32H14Z"
                fill="url(#greenGrad)"
                stroke="#00E599"
                strokeWidth="1.5"
                strokeLinejoin="round"
              />
              <path
                d="M6 32L16 16L24 32H6Z"
                fill="url(#cyanGrad)"
                opacity="0.85"
                stroke="#0A7D4C"
                strokeWidth="1.5"
                strokeLinejoin="round"
              />
              <path
                d="M24 32L32 18L42 32H24Z"
                fill="url(#emeraldGrad)"
                opacity="0.9"
                stroke="#00C48C"
                strokeWidth="1.5"
                strokeLinejoin="round"
              />
              <defs>
                <linearGradient
                  id="greenGrad"
                  x1="24"
                  y1="10"
                  x2="24"
                  y2="32"
                  gradientUnits="userSpaceOnUse"
                >
                  <stop stopColor="#00E599" />
                  <stop offset="1" stopColor="#0A7D4C" />
                </linearGradient>
                <linearGradient
                  id="cyanGrad"
                  x1="15"
                  y1="16"
                  x2="15"
                  y2="32"
                  gradientUnits="userSpaceOnUse"
                >
                  <stop stopColor="#2CD3B5" />
                  <stop offset="1" stopColor="#055B36" />
                </linearGradient>
                <linearGradient
                  id="emeraldGrad"
                  x1="33"
                  y1="18"
                  x2="33"
                  y2="32"
                  gradientUnits="userSpaceOnUse"
                >
                  <stop stopColor="#00FFB2" />
                  <stop offset="1" stopColor="#0C6B43" />
                </linearGradient>
              </defs>
            </svg>
          </div>
          <div className="ner-brand-text">
            <div className="ner-brand-title">SARVAS</div>
            <div className="ner-brand-tagline">
              Smarter Alerts. Safer Tomorrow.
            </div>
          </div>
        </div>

        {/* Center / Navigation Links */}
        <nav className={`ner-nav ${mobileMenuOpen ? "ner-nav-open" : ""}`}>
          {navItems.map((item) => (
            <a
              key={item.id}
              href={`#${item.id}`}
              onClick={(e) => handleNavClick(e, item.label)}
              className={`ner-nav-link ${activeNav === item.label ? "active" : ""}`}
            >
              {item.label}
              {activeNav === item.label && (
                <span className="ner-active-indicator" />
              )}
            </a>
          ))}
        </nav>

        {/* Mobile Hamburger Toggle */}
        <button
          type="button"
          className="ner-menu-toggle"
          onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
          aria-label="Toggle navigation menu"
        >
          {mobileMenuOpen ? (
            <X size={24} color="#ffffff" />
          ) : (
            <Menu size={24} color="#ffffff" />
          )}
        </button>
      </div>
    </header>
  );
}
