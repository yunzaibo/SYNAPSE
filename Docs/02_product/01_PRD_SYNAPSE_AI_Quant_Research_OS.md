# PRD: SYNAPSE AI-native Personal Investment Research System

## Product Goal

Build an AI-native personal investment research system that helps individual investors build, track, and evolve their investment research over time. Core = Research Memory Infrastructure / Personal Cognitive Infrastructure for investing.

P0: Factor research loop (completed). P1: Daily research loop + Market semantics + Research memory.

## Target Users

AI-native Individual Researcher (individual investors including programmers, semi-professional investors, quantitative enthusiasts, research-oriented retail investors).

## User Problem

Individual investors face:

- Research ideas are scattered, no systematic tracking
- Buy/sell decisions lack thesis documentation
- Research history is forgotten
- No way to track thesis evolution over time
- Emotional trading decisions without structured reasoning
- Information overload without research queue
- Position monitoring focuses on P&L, not research quality

## Product Solution

SYNAPSE provides 4 core features:

```txt
Daily Watchlist → "What's worth researching today?"
Position Monitor → "What's happening with my active theses?"
Factor Research → "Can I validate this quantitative hypothesis?"
Research Memory → "What did I believe, and how did it evolve?"
```

## 4 Core Features

| Feature | Positioning |
|---------|------------|
| Daily Watchlist | Research Queue, not Stock Recommendation Feed |
| Position Monitor | Active Thesis Tracker (4-layer: Portfolio → Attention → Research Flags → Thesis Context) |
| Factor Research | P0 completed (124 tests, governance-first) |
| Research Memory | Freeze cognitive state, not a trading log |

## P1 Functional Scope

P1 should support:

1. Daily Watchlist generation (WatchlistEntry with signals, risk_hint, research_angle)
2. Position Monitor (Active Thesis Tracker, 4-layer architecture)
3. Decision Memory (thesis-based buy/sell recording, optional review)
4. Research Object Model (9 objects: WatchlistEntry, Thesis, Decision, Review, Position, Signal, Risk, Event, ResearchTopic)
5. Market Semantics Layer (trading calendar, T+1, price limits, suspension, corporate actions)
6. MarketClock (research time ≠ market time)
7. Source Attribution (ai_generated / human_written / imported / market_data)
8. Thesis Evolution (append-only with parent_thesis_id)
9. Provider Abstraction (AKShare + SmartSearch data source switching)

## P1 Non-functional Requirements

- Thesis must be append-only (revision + previous_revision)
- Every AI-generated field must have source_type annotation
- MarketClock must distinguish research time from market time
- Research objects must have lifecycle states (active/inactive/archived/abandoned/superseded)
- Runtime must serve Research Lifecycle, not become the product itself

## Success Criteria

P1 is successful if a user can:

1. Open the system and see today's research queue
2. Record a buy/sell decision with thesis and key risk
3. Monitor active theses through attention and research flags
4. See thesis evolution over time (append-only history)
5. Query research memory by ticker, date, or tag

## Out of Scope (P0-P2)

- Real-money trading (architecture reserves extension points)
- Broker integration
- HFT
- Full NLP pipeline (P3)
- Multi-agent orchestration (P4/P5)
- Cloud backend / multi-tenant SaaS
- Production compliance workflow
