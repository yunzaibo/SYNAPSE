# TASK-002 Data Plane MVP

## Objective

Implement minimal local data loading and metadata validation.

## Inputs

- Local CSV / Parquet sample data
- Data metadata YAML

## Outputs

- Validated dataset object
- Data validation report

## Acceptance Criteria

- Missing required fields are detected.
- Time range is recorded.
- Available-at policy is recorded even if simplified.
