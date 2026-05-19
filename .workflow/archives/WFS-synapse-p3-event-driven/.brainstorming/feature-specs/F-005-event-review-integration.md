# F-005: Event-Review Integration

## Component #12: Link Events to Review Outcomes

### Overview
Tracks which reviews were event-driven, detects post-event thesis revisions, and maintains bidirectional referential integrity between events and reviews.

### Integration Points

#### Existing Schema Extensions
```python
# Review schema: add event reference
@dataclass
class Review(Base):
    # ... existing fields ...
    event_id: Optional[str]          # which event triggered this review
    event_trigger_type: Optional[str]  # "direct" | "propagated" | "manual"

# Decision schema: add event trigger
@dataclass
class Decision(Base):
    # ... existing fields ...
    event_trigger_id: Optional[str]
    event_influence_score: float = 0.0

# Thesis schema: add event influence
@dataclass
class Thesis(Base):
    # ... existing fields ...
    event_influences: list[str]      # event IDs that shaped this thesis
    event_influence_weight: float = 0.0
```

### Post-Event Revision Detection
- Configurable window: default 30 days after event
- Detection: thesis revision within window → link to triggering event
- False positive prevention: filter out unrelated revisions (topic mismatch)

### Bidirectional Linkage
- Event → Review: `Event.linked_review_ids` (existing)
- Review → Event: `Review.event_id` (new)
- EventContract → Reviews: aggregate review quality per event

### Tests (~10 tests)
- Event triggers review correctly
- Review links back to event
- Post-event revision detection within window
- Post-event revision detection outside window (no link)
- Bidirectional referential integrity
- Multiple events → same thesis
- Multiple reviews → same event
- Decision event trigger tracking
- Thesis event influence tracking
