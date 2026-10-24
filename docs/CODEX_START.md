# 交给 Codex 的启动提示词

## 第一次：P0 基础工程

目标：实现《问与书》SAD V1.0 的 P0 基础工程，仅做可运行骨架与安全基础。

操作：
1. 读取 `docs/PRD.md`、`docs/SAD.md`、`docs/DELIVERY.md`、`contracts/openapi.yaml`、`db/schema.sql`、`AGENTS.md`。
2. 在 `feat/p0-foundation` 分支建立 Next.js + TypeScript、FastAPI + Pydantic、SQLAlchemy + Alembic、PostgreSQL、同仓库 Worker 启动命令与 Docker Compose。
3. 实现匿名身份 Cookie + CSRF、`GET /health/live`、`GET /health/ready`，建立可注入的 LLM/Search Mock 和统一异常处理。
4. 以 Alembic 创建与 `db/schema.sql` 逻辑等价的数据库结构，自动化测试验证关键约束。
5. 建立 GitHub Actions CI：后端测试/lint、前端 lint/typecheck/build、OpenAPI 校验、空库迁移测试。
6. 首页骨架可访问但不实现每日一问的真实业务；生成 `.env.example`、README 启动方法。

约束：
- 不实现 P1—P5 业务。
- 不改 PRD 或经批准的架构契约；发现矛盾时先报告。
- 不提交密钥，不在生产部署，不动 `main`。

验收：
- 按 README 在本地启动成功；无 DeepSeek Key 也可启动。
- health 正常；匿名身份不可跨越他人会话；CSRF 缺失写请求受拒。
- 数据库迁移成功、CI 通过；接口契约校验通过。
- 输出 PR、改动文件、测试结果、手工验证、迁移及风险清单；停止等待用户验收。

## 后续阶段通用任务模板

目标：只实现 `docs/DELIVERY.md` 中 Pn 的功能与验收，不提前实现 P(n+1)。

操作：
1. `main` 同步至上一阶段 PASS 的 Tag，并新建指定 `feat/pn-...` 分支。
2. 阅读 PRD、SAD、OpenAPI、DDL 以及上一阶段验收记录。
3. 提交本阶段的代码、测试、必要迁移、文档与 PR。

约束：
- 不变更模块边界，除非先给出 ADR 并经批准。
- 第三方模型/搜索在测试中使用 Mock；不自行使用生产 Key。
- 任何接口字段变化同步 OpenAPI、后端和前端类型、验证测试。
- 不合并、不打 Tag、不部署生产，直到人工通过验收。

验收：按阶段验收表逐条列出 PASS/FAIL，并实际附上执行命令输出摘要、Commit SHA 和回滚方案。
