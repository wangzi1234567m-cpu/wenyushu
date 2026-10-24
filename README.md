# 问与书 · Codex 架构与开发交付包

版本：SAD 1.0 / 2026-10-24

## 文件

- `docs/SAD.md`：完整软件架构设计
- `contracts/openapi.yaml`：OpenAPI 3.1 外部接口基线（21项 operation）
- `db/schema.sql`：PostgreSQL 关系模式参考（Alembic 是正式迁移唯一入口）
- `docs/DELIVERY.md`：P0–P5 的验收门槛、Git/PR/Tag 规范
- `docs/CODEX_START.md`：P0 开发任务提示词及后续任务模板
- `AGENTS.md`：Codex 在仓库内必须遵守的开发约束

## 使用步骤

1. 新建私有 GitHub 仓库，下载/解压本交付包到仓库根目录。
2. **将当前对话里已经确认的完整 PRD V1.2 导出为 `docs/PRD.md`**，不要让 Codex 自行根据摘要编造一份 PRD。
3. 向 Codex 提供仓库，让其读 `AGENTS.md` 和 `docs/CODEX_START.md` 的 P0 任务。
4. P0 开发 → CI/测试 → PR → 你人工验收 PASS → 合并到 main → Tag `mvp-p0`。
5. 对 P1–P5 重复，永远一阶段一 PR，失败不合并。
6. **公众上线前**另行核实/办理实际适用备案许可和安全、版权、隐私事项。这里提供的是技术交付规范，不代表已经完成法定手续。

## 文档校验

- OpenAPI YAML 可被 Python `yaml.safe_load` 解析；结构字段需与 FastAPI 生成的 `/openapi.json` 在 CI 比对。
- DDL 未在本交付环境的真实 PostgreSQL 上执行；Codex 在 P0 必须使用 PostgreSQL 运行 Alembic 迁移验证。
- 本包不是已完成的网站源代码，不含真实 DeepSeek API Key。
