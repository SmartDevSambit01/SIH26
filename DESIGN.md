# NER Safe — Landing Page Design Specification

## 0. Purpose

Recreate the supplied reference screenshot as closely as possible.

**IMPORTANT:**
- This document is a visual reproduction specification.
- Do NOT redesign, modernize, simplify, rearrange, or "improve" the layout.
- Do NOT invent additional sections, cards, buttons, animations, statistics, or content.
- Match the reference screenshot's composition, proportions, spacing, typography hierarchy, colors, transparency, and visual density.
- The screenshot is the single source of truth for the landing-page appearance.
- If an implementation decision is necessary, choose the option that makes the rendered page look closest to the reference screenshot.
- The final website should be a real responsive React page, not an image pasted as the entire webpage.
- Use real HTML/CSS/React elements for text, buttons, cards, navigation, and search.

---

# 1. Reference

Reference image:
`Screenshot 2026-09-15 203418(1).png`

Reference image dimensions:
**1513 × 980 px**

The screenshot shows a desktop/tablet-style viewport with a cinematic Northeast India mountain landscape filling the page.

The outer black rounded device/browser frame and top notch visible in the screenshot should be treated as presentation/mockup framing rather than part of the actual web application's content, unless the developer explicitly wants the frame reproduced in a demo mockup.

The actual landing page begins at the top navigation/header and extends over the mountain background.

---

# 2. Overall Visual Direction

Brand:
**NER Safe**

Tagline:
**Smarter Alerts. Safer Tomorrow.**

Product:
**AI-Powered Early Warning & Landslide Risk Monitoring System For North Eastern Region**

Visual style:
- Government/public-safety application
- Disaster-management dashboard
- Trustworthy
- Modern
- Professional
- High-contrast
- Futuristic but practical
- Strong use of a real cinematic Northeast mountain landscape
- Glassmorphism/translucent panels over the image
- White typography over dark/transparent areas
- Green, orange, purple, blue, and red status/action colors

Do not turn this into a generic SaaS landing page.

---

# 3. Page Structure

The page is one full-screen landing/hero view.

High-level structure:

1. Full-screen mountain background
2. Top navigation/header
3. Left hero/content area
4. Right emergency-help panel
5. Three phase cards
6. Risk search card
7. Incident report action
8. NER state names near the bottom

Approximate visual composition:

```text
┌───────────────────────────────────────────────────────────────┐
│ LOGO     HOME  ALERTS  RISK MAP  REPORTS  ABOUT   Login SignUp│
├───────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────────────────────┐   ┌────────────────────────┐ │
│  │ Predict · Monitor · Protect  │   │    Emergency Help      │ │
│  │                              │   │                         │ │
│  │ AI-Powered Early Warning &   │   │          112            │ │
│  │ Landslide Risk Monitoring    │   │   Emergency Number      │ │
│  │ System For North Eastern     │   │ Police / Ambulance /    │ │
│  │ Region                       │   │ Disaster Mgmt.          │ │
│  │                              │   │                         │ │
│  │ [Pre] [During] [Post]        │   │ Quick Access             │ │
│  │                              │   │ Hospitals / Police /     │ │
│  │ [ Check Risk in Your Area ]  │   │ Emergency Shelters       │ │
│  └──────────────────────────────┘   └────────────────────────┘ │
│                                                               │
│        Report an incident                                    │
│                                                               │
│ Arunachal Pradesh   Assam   Manipur   Meghalaya   Mizoram...  │
└───────────────────────────────────────────────────────────────┘
```

---

# 4. Background Image

Use a high-resolution cinematic Northeast India mountain landscape.

The reference contains:
- Large green forested mountains
- Snow-capped/high mountain peaks in the distance
- White clouds and mist
- Deep mountain valley
- River/stream
- Winding mountain road
- Small settlement/buildings
- Rich natural landscape
- Dramatic sky

Background treatment:
- Image fills the entire page viewport.
- `background-size: cover`.
- `background-position: center`.
- No obvious tiling.
- No white margins around the webpage.
- Keep the image visible behind the translucent cards.
- Add only enough dark overlay to maintain text readability.
- Do not make the image so dark that the mountains disappear.

The reference is visually image-dominant. The mountain landscape must remain clearly visible.

---

# 5. Header / Navigation

Position:
Top of the page.

Approximate height:
**88–90 px** in the reference.

The header spans the full content width.

Background:
- Deep blue/navy translucent color.
- Slight transparency so the mountain/sky can subtly show through.
- Thin dark bottom border/shadow.

Header layout:

### Left brand block

Place the logo at the far left.

Logo:
- NER Safe mountain-style logo
- Green/teal mountain symbol
- White "NER Safe" text
- Small white tagline below:
  **Smarter Alerts. Safer Tomorrow.**

The logo block occupies approximately the left 18–20% of the header.

### Navigation

Centered/right of logo:

- HOME
- ALERTS
- RISK MAP
- REPORTS
- ABOUT

Typography:
- White
- Bold/semi-bold
- Uppercase
- Large enough to be clearly readable
- Consistent horizontal spacing

HOME is the active page:
- White text
- Underline beneath HOME
- Underline is visually prominent

### Authentication buttons

At the far right:

**Login**
- Rounded pill
- Light gray/blue translucent background
- Dark/black text
- Large horizontal padding

**Sign Up**
- Rounded pill
- Green background
- White text
- Large horizontal padding

Do not change the order:
`Login` then `Sign Up`.

---

# 6. Hero Left Panel

Position:
Upper-left/center-left of the page below the header.

The reference uses a large rounded translucent dark blue/gray panel.

Approximate:
- Width: about 53–55% of the viewport
- Large rounded corners
- Semi-transparent
- Background allows mountains to remain visible
- Subtle glass effect
- No heavy solid border

Inside the panel:

## 6.1 Top pill

At the top center of the panel:

**Predict . Monitor . Protect**

Reference appearance:
- Wide rounded capsule/pill
- Light gray/white translucent fill
- White/light text
- Centered
- Approximately 50% panel width

Keep the exact wording:
`Predict . Monitor . Protect`

Do not replace periods with arrows.

## 6.2 Main heading

Large white bold heading:

**AI-Powered Early Warning &  
Landslide Risk Monitoring System  
For North Eastern Region**

The reference wraps this into approximately 3 lines.

Typography:
- White
- Very bold
- Large desktop heading
- Tight/medium line height
- Left aligned

The heading should be one semantic H1, but visually match the screenshot.

Important:
Use exactly:

`AI-Powered Early Warning & Landslide Risk Monitoring System For North Eastern Region`

Do not change:
- North Eastern Region
- Early Warning
- Landslide Risk Monitoring System

---

# 7. Three Phase Cards

Below the hero heading, create three cards in one horizontal row.

They are:

### Card 1 — Pre-Landslide

Background:
Green, semi-transparent/solid green.

Text:
**Pre-Landslide**

Subtext:
**Risk map monitoring**

Icon:
White map/location icon.

### Card 2 — During-Landslide

Background:
Orange/amber.

Text:
**During-Landslide**

Subtext:
**Alarm Activated**

Icon:
Bell/alarm icon.

### Card 3 — Post-Landslide

Background:
Purple.

Text:
**Post-Landslide**

Subtext:
**Recovery & Support**

Icon:
Heart/recovery-style icon with red accent.

Card properties:
- Rounded corners
- Equal visual height
- Similar width
- White text
- Comfortable internal padding
- Horizontal row
- Small gap between cards

Do not convert them into large feature sections. They are compact dashboard-style cards exactly as shown.

---

# 8. Risk Search Card

Below the three phase cards, on the lower-left:

White rounded rectangular card.

Approximate:
- Width: ~550 px at reference scale
- Height: ~160 px
- Strong white background
- Large rounded corners
- No excessive shadow

Heading:

**Check Risk in Your Area**

Large black/dark text.

Below it:
A horizontal search row.

Search input:
- Light gray background
- Rounded/pill shape
- Search icon at left
- Placeholder:

**Search Location (e.g. Dibrugarh, Kahima...)**

Keep this wording as shown in the reference.

Button:
**Get Details**

Appearance:
- Green background
- White text
- Rectangular with slightly rounded corners
- Positioned immediately to the right of the search field

The input and button should fit on one row on desktop.

---

# 9. Report an Incident

Near the lower-middle area, beneath/near the phase/search area:

Camera icon followed by:

**Report an incident**

Appearance:
- Small white/light icon
- White/light text
- Subtle dark/translucent backing if required for readability
- Compact
- Looks like a quick action rather than a large CTA

Keep it visually separate from the white search card.

---

# 10. Right Emergency Help Panel

This is one of the most prominent elements.

Position:
Upper-right side below the navigation.

Large translucent glass panel.

Approximate:
- Width: ~36–38% of viewport
- Height: ~640 px at reference scale
- Rounded corners
- Transparent/glass background
- Thin subtle border
- Dark translucent body

## 10.1 Red emergency header

At the top of the panel:

Bright red rounded rectangle.

Text:

**Emergency Help**

Second line:

**(In case of immediate danger,call now)**

Keep the wording and comma placement visually close to the reference.

Typography:
- White
- Emergency Help: very bold
- Supporting line: smaller white

## 10.2 Main 112 area

Large red phone handset icon on left/near center.

Large red number:

**112**

Supporting text:

**Emergency Number  
(India)**

The number must be visually dominant.

The phone icon should be large.

The exact layout should visually resemble:

```text
[ large phone icon ]    112
                        Emergency Number
                        (India)
```

The emergency number section should occupy a substantial portion of the upper panel.

---

# 11. Emergency Service Buttons

Under the 112 area, three horizontal service cards/buttons:

### Police
Blue

Text:
**Police**
**100**

Include police/emergency icon.

### Ambulance
Green

Text:
**Ambulance**
**108**

Include ambulance icon.

### Disaster Mgmt.
Orange

Text:
**Disaster Mgmt.**
**1070**

Include bell/disaster icon.

Properties:
- Three equal/similar width cards
- Rounded corners
- White text
- Compact
- Distinct background colors

Order must remain:
`Police | Ambulance | Disaster Mgmt.`

---

# 12. Quick Access Section

Below the emergency buttons, add a divider.

Heading:

**Quick Access:**

Black/dark text in the reference.

Then three translucent/light cards in one row.

### Hospitals

Icon:
Hospital icon.

Text:
**Hospitals**

Link-style text:
**List**

### Police Stations

Icon:
Police station icon.

Text:
**Police  
Stations**

Link:
**List**

### Emergency Shelters

Icon:
Green shelter/house icon.

Text:
**Emergency  
Shelters**

Link:
**List**

The `List` text appears blue in the reference.

Do not turn these into large cards.

---

# 13. Safety Footer Strip Inside Emergency Panel

At the bottom of the emergency panel:

Dark gray rounded pill/strip.

Text:

**Your safety our priority**

White, bold, centered.

Keep this phrase exactly.

---

# 14. NER State Names

At the bottom of the visible page, place the eight North Eastern states as white text over the mountain image.

States:

1. Arunachal Pradesh
2. Assam
3. Manipur
4. Meghalaya
5. Mizoram
6. Nagaland
7. Sikkim
8. Tripura

The reference distributes them spatially across the bottom rather than putting them into a conventional list.

Approximate visual arrangement:

```text
Arunachal Pradesh       Assam          Manipur

                         Meghalaya      Mizoram

                              Sikkim        Nagaland     Tripura
```

The exact horizontal positions should follow the screenshot as closely as practical.

Typography:
- White
- Medium/large
- No cards behind them
- No bullets
- No numbered list
- No underline

---

# 15. Exact Color Direction

Use the following palette as the implementation baseline.

Primary navy:
`#123E57`

Deep dark green:
`#0C1F1B`

Primary safe green:
`#0A7D4C`

Warning orange:
`#E58925`

Critical red:
`#D02127`

Purple:
`#7139AF`

Blue:
`#0A72D0`

White:
`#F8F8F8`

Light gray:
`#C6C7C4`

Muted gray/teal:
`#53676C`

These colors are approximate visual matches and should be adjusted only when necessary to reproduce the screenshot.

---

# 16. Transparency / Glassmorphism

The reference depends heavily on transparency.

Use:
- Semi-transparent dark blue/green panels
- Semi-transparent emergency body
- White/light translucent elements
- Background image visible through panels

Suggested implementation approach:
- `backdrop-filter: blur(...)`
- Semi-transparent backgrounds using rgba/alpha
- Subtle border
- Moderate shadow

Do not overuse blur.

The mountains should remain recognizable behind the panels.

---

# 17. Typography

Use a clean modern sans-serif.

Preferred:
- Inter
- Poppins
- or another visually close geometric sans-serif

Hierarchy:

H1:
Very large, bold, white.

Navigation:
Large, bold, white.

Emergency heading:
Bold white.

Cards:
Bold title + normal/light supporting text.

State names:
Medium weight white.

Search heading:
Large dark text.

Avoid:
- Serif fonts
- Decorative fonts
- Handwritten fonts
- Excessive letter spacing

---

# 18. Icons

Use a consistent icon library such as Lucide React or another clean outline icon library.

Required visual categories:

- Search
- Map/location
- Bell/alarm
- Recovery/heart
- Camera
- Phone
- Police
- Ambulance
- Disaster alert
- Hospital
- Police station
- Emergency shelter

Important:
Icons should visually resemble the reference.
Do not use random emoji unless the implementation specifically needs to match the reference's emoji-like appearance.

If using Lucide:
- `Search`
- `MapPinned` / `Map`
- `Bell`
- `HeartPulse` / appropriate recovery icon
- `Camera`
- `Phone`
- `Hospital`
- `Shield`
- `House`
etc.

---

# 19. Spacing and Proportions

The page should feel dense like the reference.

Do NOT:
- Make huge empty gaps
- Push the emergency card too far down
- Move the hero to the center
- Make cards full width
- Turn the page into a scrolling marketing website

The reference is essentially a **full-screen operational landing dashboard**.

Maintain:
- Header at top
- Hero left
- Emergency panel right
- Phase cards below hero
- Search card below phase cards
- State names near bottom

---

# 20. Desktop Layout

Target desktop design:
**1440–1536 px wide**

At desktop:
- Header full width
- Hero left approximately 55%
- Emergency panel right approximately 37%
- Small center gap
- Background covers entire viewport
- All major content visible without requiring scrolling at 980–1024 px height

The target screenshot is approximately:
**1513 × 980 px**

The design should visually fit within a 980–1024 px height desktop viewport.

---

# 21. Responsive Behavior

The screenshot is desktop-first, but the actual website must remain usable on smaller screens.

Do NOT change the desktop appearance.

For smaller widths only:

- Navigation may collapse into a hamburger menu.
- Hero and emergency panel may stack vertically.
- Three phase cards may become a 1-column or 2-column layout.
- Search controls may wrap.
- State names may become a grid/list.
- Emergency service buttons may wrap.

The responsive version should preserve the same visual language and colors.

---

# 22. Interactions

The screenshot represents the visual state, but these elements should be functional:

### HOME
Navigate to landing page.

### ALERTS
Navigate to alerts page.

### RISK MAP
Navigate to live risk map.

### REPORTS
Navigate to reports page.

### ABOUT
Navigate to about page.

### Login
Open login page/modal.

### Sign Up
Open registration page/modal.

### Get Details
Use the entered location to navigate to a location-risk page.

### Search Location
Allow typing a location.

### Report an incident
Navigate to citizen incident-reporting page.

### Hospitals / Police Stations / Emergency Shelters
Open the corresponding list/map view.

### Emergency service buttons
Use appropriate phone-link behavior on supported devices.

Do not invent additional functionality on the landing page.

---

# 23. Component Structure

Suggested React component structure:

```text
LandingPage
├── Header
│   ├── BrandLogo
│   ├── Navigation
│   └── AuthButtons
│
├── HeroSection
│   ├── HeroPanel
│   │   ├── MottoPill
│   │   ├── MainHeading
│   │   └── PhaseCards
│   │       ├── PreLandslideCard
│   │       ├── DuringLandslideCard
│   │       └── PostLandslideCard
│   │
│   ├── RiskSearchCard
│   └── ReportIncidentAction
│
├── EmergencyPanel
│   ├── EmergencyHeader
│   ├── Emergency112
│   ├── EmergencyServiceButtons
│   ├── QuickAccess
│   │   ├── Hospitals
│   │   ├── PoliceStations
│   │   └── EmergencyShelters
│   └── SafetyStrip
│
└── NERStates
```

---

# 24. Important Content — Do Not Change

Use exactly these primary strings:

### Brand
`NER Safe`

### Tagline
`Smarter Alerts. Safer Tomorrow.`

### Motto
`Predict . Monitor . Protect`

### Hero
`AI-Powered Early Warning & Landslide Risk Monitoring System For North Eastern Region`

### Phase 1
`Pre-Landslide`
`Risk map monitoring`

### Phase 2
`During-Landslide`
`Alarm Activated`

### Phase 3
`Post-Landslide`
`Recovery & Support`

### Search
`Check Risk in Your Area`

Placeholder:
`Search Location (e.g. Dibrugarh, Kahima...)`

Button:
`Get Details`

### Emergency
`Emergency Help`
`(In case of immediate danger,call now)`

`112`

`Emergency Number`
`(India)`

`Police`
`100`

`Ambulance`
`108`

`Disaster Mgmt.`
`1070`

### Quick Access
`Quick Access:`

`Hospitals`
`List`

`Police Stations`
`List`

`Emergency Shelters`
`List`

### Safety
`Your safety our priority`

### Incident
`Report an incident`

### Navigation
`HOME`
`ALERTS`
`RISK MAP`
`REPORTS`
`ABOUT`

### Authentication
`Login`
`Sign Up`

### States
`Arunachal Pradesh`
`Assam`
`Manipur`
`Meghalaya`
`Mizoram`
`Nagaland`
`Sikkim`
`Tripura`

---

# 25. What NOT to Add

Do NOT add:

- Pricing
- Testimonials
- Blog
- Extra statistics
- Fake AI accuracy
- Fake weather values
- Fake soil moisture values
- Fake live alerts
- Fake landslide predictions
- Extra navigation items
- Footer sections not visible in the reference
- Large "Get Started" CTA
- Extra illustrations
- Stock cards
- Generic SaaS sections
- Chatbot widget
- Cookie banner
- Floating social-media buttons

The landing page should stay visually faithful to the reference.

---

# 26. Data / AI Integration Rule

The landing page is primarily a visual/navigation page.

Do not hard-code fake live disaster data into the landing page.

When real backend data becomes available:
- Risk map should consume the real risk API.
- Alerts should consume real alert data.
- Location details should consume the actual risk-analysis API.
- Soil moisture should come from the actual satellite/data pipeline.
- Rainfall should come from the actual data source.
- AI predictions should only display model-generated values.

Never label mock/replay data as live.

---

# 27. Image Handling

If the exact background image is available in the project assets, use it.

If not, create an asset placeholder:

```text
frontend/public/assets/ner-mountain-background.jpg
```

The background should be high resolution.

Do not crop the image in a way that removes the major mountain/road/valley composition visible in the reference.

Use CSS:

```css
background-size: cover;
background-position: center;
```

Adjust `background-position` if necessary to visually match the screenshot.

---

# 28. Browser / Device Frame Clarification

The supplied screenshot includes a black rounded outer frame and a top-center notch.

For the actual website:

**Do not add a fake browser/device frame around the webpage.**

The website should render directly in the browser viewport.

The frame is treated as the presentation context of the supplied screenshot, not the web application itself.

The internal page content — header, mountain background, hero panel, emergency panel, cards, search, report action, and state names — is what must be reproduced.

---

# 29. Final Visual Acceptance Checklist

Before considering the landing page complete, compare the browser render against the reference screenshot.

Check:

- [ ] Same overall composition
- [ ] Same mountain background feel
- [ ] Header at same height/proportion
- [ ] NER Safe logo in same location
- [ ] Navigation order identical
- [ ] HOME active/underlined
- [ ] Login and Sign Up in same position
- [ ] Hero panel on left
- [ ] Motto pill at top of hero
- [ ] H1 wraps into approximately 3 lines
- [ ] Three phase cards in one row
- [ ] Correct green/orange/purple card colors
- [ ] Search card below phase cards
- [ ] Report incident near lower center
- [ ] Emergency panel on right
- [ ] Red Emergency Help header
- [ ] Large 112 section
- [ ] Police / Ambulance / Disaster Mgmt. row
- [ ] Quick Access section
- [ ] Hospitals / Police Stations / Emergency Shelters
- [ ] Blue List links
- [ ] Safety strip at bottom of emergency panel
- [ ] Eight NER state names at bottom
- [ ] Correct white/blue/green/orange/red/purple palette
- [ ] Correct transparency/glass effect
- [ ] No unnecessary additional sections
- [ ] No fake data
- [ ] No visual redesign

---

# 30. Developer Instruction

When implementing this page:

1. First reproduce the desktop screenshot as closely as possible.
2. Do not build the entire rest of the application at the same time.
3. Create reusable React components.
4. Keep styling organized.
5. Use the supplied background asset.
6. Use real text, not text baked into an image.
7. Make buttons and navigation functional.
8. Make the page responsive only after the desktop version matches the reference.
9. Compare the rendered result with the reference screenshot and adjust spacing, sizing, transparency, and positioning.
10. Do not replace the reference design with a different "better" design.

**Priority order:**

```text
1. Visual similarity
2. Layout/proportions
3. Typography
4. Colors
5. Transparency
6. Icons
7. Responsive behavior
8. Functionality
```

The goal is:

**REFERENCE SCREENSHOT → AS CLOSE AS POSSIBLE IN A REAL REACT WEBSITE**
