# Target User and Use Cases

## Primary User

AI-native Individual Researcher — individual investors including programmers, semi-professional investors, quantitative enthusiasts, and research-oriented retail investors.

## User Persona 1: Individual Investor (Research-oriented)

Needs:

- Daily research queue of stocks worth investigating
- Track research theses behind buy/sell decisions
- Record reasoning, not just outcomes
- Avoid emotional trading decisions
- Build a personal research memory over time

## User Persona 2: AI-native Developer / Quant Enthusiast

Needs:

- Reproducible factor research workflow
- Use AI coding safely
- Keep architecture clean
- Fork and modify the system

## User Persona 3: Semi-professional Investor

Needs:

- Systematic research workflow
- Position monitoring through thesis lens
- Research memory accumulation
- Decision review and pattern recognition

## Multi-end Strategy

- **Desktop**: Windows/Mac desktop application
- **Mobile**: Feishu/WeChat Bot for mobile notifications
- **User mode**: Natural language first (AI-assisted), technical users can fork and modify

## P0 Use Cases

### UC-001: Create a Research Project

User creates a new research project and selects the initial domain: cross-sectional equity factor research.

### UC-002: Define a Factor

User defines a factor with name, description, inputs, calculation logic, frequency, universe, and assumptions.

### UC-003: Audit a Factor

System calculates or records coverage, missing rate, distribution, IC / RankIC, stability, factor correlation, and leakage risk notes.

### UC-004: Run a Backtest

System runs a simple portfolio simulation or calls a backtest engine with explicit assumptions.

### UC-005: Generate a Report

System generates a research report with hypothesis, data, factor definition, validation result, backtest result, risks, and next experiments.

### UC-006: AI-assisted Research Plan

User asks the AI assistant to draft a research plan. The assistant produces a structured plan, not unsafe actions.

## P1 Use Cases

### UC-101: Daily Watchlist Generation

System generates a daily research queue with WatchlistEntry objects (ticker, headline, why_now, signals, signal_strength, risk_hint, research_angle, action).

### UC-102: Position Monitoring

System monitors active research theses through 4-layer Active Thesis Tracker (Portfolio State → Attention State → Research Flags → Thesis Context).

### UC-103: Decision Memory Recording

User records buy/sell decisions with thesis, key_risk, time_horizon. Review is optional but system-suggested.

### UC-104: Research Object Management

System manages 9 research objects (WatchlistEntry, Thesis, Decision, Review, Position, Signal, Risk, Event, ResearchTopic) with full relationship tracking.
