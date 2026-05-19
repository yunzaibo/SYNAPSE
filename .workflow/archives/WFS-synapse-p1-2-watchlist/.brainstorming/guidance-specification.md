# P1-2 Daily Watchlist Generator - Confirmed Guidance Specification

**Metadata**: 2026-05-19T21:30:00+08:00 | Type: feature | Focus: watchlist-scoring | Roles: system-architect, data-architect, product-manager

## 1. Project Positioning & Goals

**CONFIRMED Objectives**:
- 实现 P1-2 Daily Watchlist Generator — 基于 P1 Market Semantics 和 P5 DataSource 的个性化每日关注列表生成器
- 整合信号评分、事件驱动、持仓状态，生成个性化每日关注列表
- 依赖 P1-1 Market Semantics（交易日历、复权、北向资金、指数成分）和 P5 DataSource 适配器

**CONFIRMED Success Criteria**:
- 每日关注列表包含优先级评分（priority_score）
- 事件驱动过滤基于 Event lifecycle decay model
- 持仓状态感知基于 Position thesis_status 和 attention_state
- 市场语义验证基于 TradingCalendar、NorthboundFlow、IndexConstituent
- 个性化推荐基于用户配置的评分权重

## 2. Concepts & Terminology

**Core Terms**: The following terms are used consistently throughout this specification.

| Term | Definition | Aliases | Category |
|------|------------|---------|----------|
| WatchlistEntry | 每日关注列表条目，包含 symbol、priority_score、reason、source 等字段 | 关注列表条目 | core |
| Signal Scoring | 基于 Signal、Event、Position 等多维度数据计算优先级分数 | 信号评分 | core |
| Event-driven | 基于 Event lifecycle decay model 的时间衰减评分机制 | 事件驱动 | core |
| Portfolio-aware | 基于 Position thesis_status 和 attention_state 的持仓感知机制 | 持仓感知 | core |
| Market Semantics | 市场语义层，包括 TradingCalendar、NorthboundFlow、IndexConstituent | 市场语义 | core |
| Daily Generation | 每日全量再生（非增量更新），遵循 ADR-009 | 每日生成 | core |
| Priority Score | 优先级分数，0.0-1.0 之间，越高越重要 | 优先级分数 | core |
| Ranking | 基于 priority_score 的排序机制 | 排序 | core |
| Filtering | 基于市场语义和用户配置的过滤机制 | 过滤 | core |
| Personalization | 基于用户配置的评分权重和过滤规则的个性化机制 | 个性化 | core |

**Usage Rules**:
- All documents MUST use the canonical term
- Aliases are for reference only
- New terms introduced in role analysis MUST be added to this glossary

## 3. Non-Goals (Out of Scope)

The following are explicitly OUT of scope for this project:

- **实时推送**: 本次只做每日批量生成，不实现实时推送通知
- **复杂 UI**: 只提供数据接口（JSON/YAML），不实现 Web 或移动端 UI
- **机器学习推荐**: 基于规则的评分机制，不引入机器学习模型
- **多市场支持**: 只支持 A 股市场，不支持港股、美股等
- **历史回测**: 只关注当日生成，不实现场景回测功能
- **自定义评分公式**: 评分公式固定，不支持用户自定义公式

**Rationale**: These exclusions help maintain focus on core objectives and prevent scope creep.

## 4. System Architect Decisions

### SELECTED Choices

**架构风格**: 采用 Projection 架构模式，watchlist_generator 作为 4 个 Projection 之一
- **Rationale**: 现有架构已经采用 Projection 模式，watchlist_generator 是其中一部分
- **Impact**: 保持架构一致性，易于维护和扩展
- **Requirement Level**: MUST

**数据流**: 采用 Daily Full Regeneration 模式，每日重新生成整个关注列表
- **Rationale**: 遵循 ADR-009，避免增量更新的复杂性和状态管理问题
- **Impact**: 简化实现，但可能增加计算量
- **Requirement Level**: MUST

**依赖管理**: 采用 Dependency Injection 模式，通过函数参数传递依赖
- **Rationale**: 现有代码已经采用此模式，保持一致性
- **Impact**: 便于测试和配置
- **Requirement Level**: SHOULD

**错误处理**: 采用 Graceful Degradation 策略，数据源不可用时返回空结果
- **Rationale**: 避免单点故障影响整个系统
- **Impact**: 系统可用性提高，但可能丢失部分数据
- **Requirement Level**: SHOULD

**配置管理**: 采用 YAML 配置文件，支持评分权重和过滤规则
- **Rationale**: 现有代码已经采用 YAML 配置，保持一致性
- **Impact**: 便于用户自定义配置
- **Requirement Level**: MAY

### Cross-Role Considerations

**Schema Extension**: WatchlistEntry 需要新增 priority_score 和 reason 字段
- **Affected Roles**: data-architect, system-architect
- **Decision**: 采用 Lazy Upcast 模式，新字段添加默认值，保持向后兼容
- **Requirement Level**: MUST

**SignalType 枚举**: WatchlistEntry.SignalType 与 schemas/signal.py.SignalType 是独立枚举
- **Affected Roles**: data-architect, system-architect
- **Decision**: 保持两个独立枚举，避免修改现有定义
- **Requirement Level**: MUST

## 5. Data Architect Decisions

### SELECTED Choices

**Schema 设计**: WatchlistEntry 新增 priority_score (float) 和 reason (str) 字段
- **Rationale**: 优先级评分和原因是核心功能需求
- **Impact**: 需要更新 to_dict/from_dict 方法，添加 round-trip 测试
- **Requirement Level**: MUST

**数据存储**: 采用 YAML 格式存储关注列表，Parquet 格式存储评分配置
- **Rationale**: 现有代码已经采用 YAML 存储，保持一致性
- **Impact**: 便于阅读和编辑，但可能影响性能
- **Requirement Level**: SHOULD

**数据模型**: 采用 Frozen Dataclass 模式，不可变数据模型
- **Rationale**: 现有代码已经采用此模式，保持一致性
- **Impact**: 线程安全，易于缓存
- **Requirement Level**: MUST

**ID 生成**: 采用 generate_id('wl') 生成唯一标识符
- **Rationale**: 现有代码已经采用此模式，保持一致性
- **Impact**: 唯一性保证，便于追踪
- **Requirement Level**: MUST

**序列化**: 采用 to_dict/from_dict 往返序列化模式
- **Rationale**: 现有代码已经采用此模式，保持一致性
- **Impact**: 便于存储和加载
- **Requirement Level**: MUST

### Cross-Role Considerations

**Schema 版本**: WatchlistEntry schema 需要版本升级
- **Affected Roles**: data-architect, system-architect
- **Decision**: 采用 Lazy Upcast 模式，新字段添加默认值，保持向后兼容
- **Requirement Level**: MUST

**枚举管理**: 保持 WatchlistEntry.SignalType 与 schemas/signal.py.SignalType 独立
- **Affected Roles**: data-architect, system-architect
- **Decision**: 不修改现有枚举定义，避免破坏现有代码
- **Requirement Level**: MUST

## 6. Product Manager Decisions

### SELECTED Choices

**功能优先级**: P1-2 核心功能优先，扩展功能后续迭代
- **Rationale**: MVP 优先，确保核心功能稳定
- **Impact**: 缩短开发周期，但可能缺少部分功能
- **Requirement Level**: MUST

**用户体验**: 关注列表按优先级排序，支持过滤和搜索
- **Rationale**: 用户需要快速找到最重要的关注点
- **Impact**: 提高用户效率，但可能增加实现复杂度
- **Requirement Level**: SHOULD

**个性化**: 支持用户配置评分权重和过滤规则
- **Rationale**: 不同用户有不同的关注点和偏好
- **Impact**: 提高用户满意度，但可能增加配置复杂度
- **Requirement Level**: MAY

**数据源**: 优先支持 EastMoney 和 Akshare 数据源
- **Rationale**: 现有代码已经支持这两个数据源
- **Impact**: 覆盖主要数据需求，但可能缺少其他数据源
- **Requirement Level**: SHOULD

**测试覆盖**: 核心功能测试覆盖率 > 80%
- **Rationale**: 确保核心功能稳定可靠
- **Impact**: 提高代码质量，但可能增加开发时间
- **Requirement Level**: SHOULD

### Cross-Role Considerations

**功能范围**: P1-2 只关注每日关注列表生成，不包含实时推送
- **Affected Roles**: product-manager, system-architect
- **Decision**: 每日批量生成，不实现实时推送
- **Requirement Level**: MUST

**UI 范围**: 只提供数据接口，不实现 Web 或移动端 UI
- **Affected Roles**: product-manager, system-architect
- **Decision**: 提供 JSON/YAML 数据接口
- **Requirement Level**: MUST

## 7. Cross-Role Integration

**CONFIRMED Integration Points**:
- **Schema Extension**: WatchlistEntry 新增 priority_score 和 reason 字段，需要 data-architect 和 system-architect 协作
- **Market Semantics Integration**: 集成 P1-1 Market Semantics（TradingCalendar、NorthboundFlow、IndexConstituent），需要 system-architect 和 data-architect 协作
- **Event-driven Scoring**: 集成 Event lifecycle decay model，需要 system-architect 和 product-manager 协作
- **Portfolio-aware Scoring**: 集成 Position thesis_status 和 attention_state，需要 system-architect 和 product-manager 协作
- **Data Source Integration**: 集成 P5 DataSource（EastMoney、Akshare），需要 system-architect 和 data-architect 协作

## 8. Risks & Constraints

**Identified Risks**:
- **Schema Breaking Change**: WatchlistEntry schema 新增字段可能导致现有代码失败 → Mitigation: 采用 Lazy Upcast 模式，新字段添加默认值
- **Performance Impact**: 每日全量再生可能影响性能 → Mitigation: 优化算法，缓存中间结果
- **Data Source Availability**: 数据源不可用可能导致评分不准确 → Mitigation: 采用 Graceful Degradation 策略，返回空结果
- **Configuration Complexity**: 用户配置可能过于复杂 → Mitigation: 提供合理默认值，简化配置界面

## 9. Next Steps

**⚠️ Automatic Continuation** (when called from auto mode):
- Auto mode assigns agents for role-specific analysis
- Each selected role gets conceptual-planning-agent
- Agents read this guidance-specification.md for context

## 10. Feature Decomposition

**Constraints**: Max 8 features | Each independently implementable | ID format: F-{3-digit}

| Feature ID | Name | Description | Related Roles | Priority |
|------------|------|-------------|---------------|----------|
| F-021 | watchlist-schema-extension | WatchlistEntry schema 新增 priority_score 和 reason 字段 | data-architect, system-architect | High |
| F-022 | signal-scoring-engine | 基于 Signal、Event、Position 等多维度数据计算优先级分数 | system-architect, product-manager | High |
| F-023 | event-driven-filtering | 基于 Event lifecycle decay model 的时间衰减评分机制 | system-architect, product-manager | High |
| F-024 | portfolio-aware-scoring | 基于 Position thesis_status 和 attention_state 的持仓感知机制 | system-architect, product-manager | High |
| F-025 | market-semantics-validation | 集成 P1-1 Market Semantics（TradingCalendar、NorthboundFlow、IndexConstituent） | system-architect, data-architect | Medium |
| F-026 | ranking-and-filtering | 基于 priority_score 的排序和过滤机制 | product-manager, system-architect | Medium |
| F-027 | personalization-config | 支持用户配置评分权重和过滤规则 | product-manager, data-architect | Low |
| F-028 | watchlist-tests | 扩展 test_projection.py，添加 scoring/ranking/filtering 测试 | system-architect, data-architect | High |

## Appendix: Decision Tracking

| Decision ID | Category | Question | Selected | Phase | Rationale |
|-------------|----------|----------|----------|-------|-----------|
| D-001 | Intent | 核心目标 | 实现 P1-2 Daily Watchlist Generator | 1 | 基于 P1 Market Semantics 和 P5 DataSource |
| D-002 | Roles | 角色选择 | system-architect, data-architect, product-manager | 2 | 覆盖架构、数据、产品三个维度 |
| D-003 | System | 架构风格 | Projection 架构模式 | 3 | 保持架构一致性 |
| D-004 | System | 数据流 | Daily Full Regeneration | 3 | 遵循 ADR-009 |
| D-005 | Data | Schema 设计 | 新增 priority_score 和 reason 字段 | 3 | 核心功能需求 |
| D-006 | Product | 功能优先级 | P1-2 核心功能优先 | 3 | MVP 优先 |
| D-007 | Cross | Schema Extension | 采用 Lazy Upcast 模式 | 4 | 保持向后兼容 |
| D-008 | Cross | SignalType 枚举 | 保持两个独立枚举 | 4 | 避免修改现有定义 |
