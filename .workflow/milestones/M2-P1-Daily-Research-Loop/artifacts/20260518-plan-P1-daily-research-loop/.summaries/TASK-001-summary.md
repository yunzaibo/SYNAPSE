# TASK-001 Summary: Workspace + Storage Infrastructure

## Status: COMPLETED

## Changes
- Created: `synapse/core/config_v2.py` (62 lines) — GlobalConfig dataclass + load_workspace_config
- Created: `synapse/core/workspace_v2.py` (101 lines) — WorkspaceManager class
- Created: `tests/unit/test_config_v2.py` (78 lines) — 6 tests
- Created: `tests/unit/test_workspace_v2.py` (117 lines) — 13 tests

## Summary
实现了 Workspace + Storage 基础设施，包含 TOML 全局配置加载和 workspace 目录管理。所有 19 个测试通过。

## Key Decisions
1. **dataclass 而非 dict** — GlobalConfig 用 dataclass 提供类型安全和默认值
2. **WORKSPACE_DIRS 包含 .index/** — 按 Research Object Schema 定义，10 个标准目录完整覆盖
3. **init_workspace 同时创建 synapse.yaml** — 保持 workspace 自描述

## Convergence Criteria
| Criterion | Status |
|-----------|--------|
| workspace_v2.py exists with WorkspaceManager | ✅ |
| init_workspace() creates all 10 dirs | ✅ |
| load_workspace_config() reads synapse.yaml | ✅ |
| config_v2.py exists with GlobalConfig | ✅ |
| GlobalConfig.load() reads config.toml | ✅ |
| tests/unit/test_workspace_v2.py passes | ✅ (13/13) |
| tests/unit/test_config_v2.py passes | ✅ (6/6) |

## Validation
✅ Tests: 19/19 passing
✅ No existing tests broken
