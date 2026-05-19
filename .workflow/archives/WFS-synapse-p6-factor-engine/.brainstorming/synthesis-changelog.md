# Synthesis Changelog: P6 因子研究引擎

**Session**: WFS-synapse-p6-factor-engine
**Date**: 2026-05-19

---

## Phase 3: Role Analysis

| Role | Key Findings | File |
|------|-------------|------|
| system-architect | Registry+Plugin 模式, BaseFactor ABC, PartialResult 错误隔离 | system-architect/analysis.md |
| data-architect | FactorSpec 继承 BaseSchema, Parquet 存储, point-in-time 校验 | data-architect/analysis.md |
| subject-matter-expert | A-share 6M-1M 动量, ICIR 评级标准, T+1 约束 | analysis/subject-matter-expert.md |

## Phase 4: Synthesis Decisions

### D1: FactorSpec 设计
- **Decision**: FactorSpec 使用独立 dataclass，不继承 BaseSchema
- **Rationale**: Factor 元数据与 Event/Thesis 生命周期不同，独立更灵活
- **Trade-off**: 失去与 YAML 存储层的统一，但获得更简洁的接口

### D2: 存储策略
- **Decision**: 因子值存 Parquet，元数据存 JSON
- **Rationale**: 大规模因子矩阵 YAML 序列化不可接受
- **Trade-off**: 增加 Parquet 依赖，但获得列式存储性能

### D3: 评级标准
- **Decision**: 基于 ICIR 的 A/B/C/D 评级
- **Rationale**: ICIR 比单一 IC 更稳健，综合考虑均值和稳定性
- **Thresholds**: A>=0.5, B>=0.3, C>=0.1, D<0.1

### D4: 因子类别优先级
- **Decision**: P0=FactorSpec+Engine+Auditor, P1=Traditional+Portfolio, P2=Decay+Event
- **Rationale**: 基础设施优先，传统因子验证，事件因子作为差异化

### D5: A-share 特殊处理
- **Decision**: 内置涨跌停、停牌、T+1 处理
- **Rationale**: A-share 市场独特性，不处理会导致因子计算错误
- **Implementation**: 在 FactorEngine 数据预处理层统一处理

## Files Generated

| File | Description |
|------|-------------|
| guidance-specification.md | 术语表 + Non-Goals + Constraints |
| feature-index.json | 7 个 feature 的索引和依赖图 |
| feature-specs/F-010*.md | FactorSpec & Registry |
| feature-specs/F-011*.md | FactorEngine Core |
| feature-specs/F-012*.md | IC/RankIC Auditor |
| feature-specs/F-013*.md | Traditional Factors |
| feature-specs/F-014*.md | Factor Portfolio Optimizer |
| feature-specs/F-015*.md | Factor Decay Analysis |
| feature-specs/F-016*.md | Event Factor Integration |
