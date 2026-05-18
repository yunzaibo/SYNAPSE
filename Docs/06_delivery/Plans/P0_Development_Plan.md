# P0 Development Plan

## Goal

Build the minimum useful research loop for SYNAPSE.

```txt
sample data
→ factor definition
→ factor audit
→ simple backtest
→ risk checklist
→ report
```

## P0 Deliverables

1. Project skeleton
2. Sample data contract
3. Factor contract
4. Experiment record
5. Simple factor audit
6. Simple backtest interface
7. Report generator
8. AI assistant prompt templates
9. P0 test plan

## Suggested Implementation Order

### Phase 0: Project Skeleton

- Create repository structure
- Add docs
- Add sample configs
- Add artifact folders

### Phase 1: Data Plane MVP

- Load local sample data
- Validate data schema
- Record metadata

### Phase 2: Factor Plane MVP

- Define factor spec
- Compute or load factor
- Generate factor audit artifact

### Phase 3: Experiment Plane MVP

- Create experiment record
- Store parameters
- Store artifacts

### Phase 4: Backtest MVP

- Run simple backtest
- Record assumptions
- Generate metrics

### Phase 5: Report MVP

- Generate markdown report
- Link artifacts
- Include risk checklist

### Phase 6: AI Assistant MVP

- Draft research plan
- Explain results
- Generate report draft

## Do Not Implement in P0

- Real trading
- Broker API
- Complex UI
- Distributed execution
- Multi-agent orchestration
- Full RAG
- Cloud backend
