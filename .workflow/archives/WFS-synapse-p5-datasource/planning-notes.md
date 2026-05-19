# Planning Notes — WFS-synapse-p5-datasource

## User Intent

**GOAL**: P5-1 真实数据源接入 — 替换 mock 数据，接入真实 A 股数据源 API

**SCOPE**:
- 东方财富 API（6 个接口：行情/资金流向/板块/基金估值/基金信息/基金搜索）
- UZI-Skill 已有 fetcher 模式（akshare 库，22 个维度）
- 其他数据源由用户后续补充

**CONTEXT**:
- P4 已完成 PollingSource + StreamBuffer + StreamingIngestion 基础设施
- 当前 streaming.py 的 fetch 是 mock 实现
- UZI-Skill 在 D:\AI\UZI-Skill，使用 akshare 作为主要数据源
- 东方财富 API 无需认证，但有频率限制

**KEY_CONSTRAINTS**:
- 接口设计必须可插拔（不绑定具体数据源）
- MVP 范围：先实现 1-2 个 adapter，预留扩展点
- 遵循 P4 架构：PollingSource 配置 + set_fetch_fn 替换
