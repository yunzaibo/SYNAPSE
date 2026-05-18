# TASK-004 Summary: File Naming + Revision Mechanism

## Status: COMPLETED

## Changes
- Created: `synapse/core/naming.py` (66 lines) — ID 生成 + 文件命名规则
- Created: `synapse/core/revision.py` (143 lines) — Thesis append-only 修订管理
- Created: `tests/unit/test_naming.py` (83 lines) — 14 tests
- Created: `tests/unit/test_revision.py` (117 lines) — 17 tests

## Summary
实现了文件命名规范和 Thesis append-only revision 机制。所有 31 个测试通过。

## Key Design
- **ID 生成**: uuid4().hex[:6] 保证唯一性，prefix_ 前缀便于识别
- **Append-only**: rev-001.md, rev-002.md... 永不覆盖，meta.yaml 始终指向最新版本
- **ThesisDir**: 辅助类封装目录操作，支持 revision 列表/编号/读写

## Convergence Criteria
| Criterion | Status |
|-----------|--------|
| naming.py exists with generate_id() | ✅ |
| generate_id('ths') starts with 'ths_' and length 10 | ✅ |
| thesis_dir returns correct format | ✅ |
| revision.py exists with create_revision() | ✅ |
| create_revision() creates rev-001.md | ✅ |
| tests pass | ✅ (31/31) |
