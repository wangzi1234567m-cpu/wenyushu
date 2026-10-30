# 《问与书》Codex 分阶段交付、验收与 Git 规范

版本：1.0 · 2026-10-24

## A. 从文档到代码的约束

1. PRD V1.2 为用户行为目标；`SAD.md` 为模块边界；`contracts/openapi.yaml` 是外部 API 契约；`db/schema.sql` 是数据结构参考（Alembic 才是运行迁移的唯一方式）。
2. Codex **每轮只做一个阶段**。本阶段验收失败时只修本阶段问题，禁止“顺手”扩展下一阶段。
3. 所有阶段都要能本地启动/Mock 演示；无 DeepSeek API Key 也能运行契约测试和 Mock 主路径。
4. 功能特性需有：实现、测试、验收、PR、合并、里程碑 Tag 五个步骤。
5. 产品团队在验收记录中记下实际执行的命令、返回结果、失败项、截图/录屏链接（UI 阶段）与版本 SHA，不能只让 AI 自述“测试通过”。

## B. 仓库组织

```text
wenyushu/
  AGENTS.md
  docs/
    PRD.md                 # 由已批准的 PRD V1.2 原文另存
    SAD.md                 # 本架构文档
    DELIVERY.md
    adr/                   # 架构变更记录
    acceptance/            # 每阶段人类验收记录
  contracts/openapi.yaml
  db/schema.sql            # 逻辑基线；正式迁移由 Alembic 提供
  web/                     # Next.js + TypeScript
  backend/
    app/api/v1/
    app/modules/{content,exploration,reading,catalog,conversation,discussion,handoff,identity,safety}/
    app/integrations/{llm,search}/
    app/infrastructure/{db,settings,logging}/
    alembic/
    tests/
  infra/
    compose.yaml
    nginx/                 # 可选生产配置
  .github/workflows/ci.yml
  .env.example
  README.md
```

> P0 阶段先创建所有必需顶级目录，不必预建未来模块中的空文件。扩展 MasterDialogue 时新建其业务模块/策略，不修改 Conversation 核心字段。

## C. 分阶段开发与验收

**2026-10-27 范围修订（用户明确要求，ADR-013）**：本次 P1 改为立场→多选理由与补充→真实 DeepSeek 持续讨论；将必要的 ConversationRuntime/DiscussionPolicy 前移到同一分支。推荐入口只导航到独立预留页，不触发推荐或检索。P1 需增加流式、消息幂等/失败/并发/越权、上下文摘要及刷新恢复验收。下表为原始阶段基线；本次 P1 以此修订及 `acceptance/P1_DISCUSSION.md` 为准。P2 的书目检索核验、P3 剩余质量/安全验收、P4 Handoff 仍分别验收，不因本次实现视为完成。

| 阶段 | 分支 | 交付边界 | 最低自动化检查 | 人工验收 | Tag |
|---|---|---|---|---|---|
| P0 基础工程 | `feat/p0-foundation` | Next/FastAPI/PG/Compose、Alembic、匿名 Cookie 与 CSRF、OpenAPI、健康检查、CI、Mock provider | CI 绿；迁移空库成功；health 200；越权测试 | 在 Win11 本地一条命令运行；无真 Key 能看到首页骨架 | `mvp-p0` |
| P1 今日一问 | `feat/p1-daily-exploration` | 题库版本、北京时间排期、选项分支、Explore→ReadingIntent；推荐使用 Mock | 日期/版本/非法选项/重复答案/读意图契约 | 从首页到选项完成，不调用真模型 | `mvp-p1` |
| P2 找书与推荐 | `feat/p2-book-recommendation` | 三种独立找书入口、DeepSeek provider、按需 Search、核验、Job Worker、结果页 | Model/Search Mock、错误 JSON、429/超时、0/1/2/3 书、幂等、无假 verified | 至少30条用例人工抽检，且能在禁联网情况下测试 | `mvp-p2` |
| P3 思辨对话 | `feat/p3-discussion-runtime` | DiscussionPolicy、会话/消息、SSE、最近消息+压缩摘要、断线恢复、安全反馈 | 并发、幂等、失败续聊、摘要观点变化、越权 | 能连续聊天，不调用推荐服务；刷新能恢复已完成消息 | `mvp-p3` |
| P4 按需阅读联动 | `feat/p4-discussion-handoff` | 快照固化、阅读意图提取、任务联动、右侧/底部书单、不打断对话 | 快照边界、任务复用、越权、模型故障隔离、对话不中断 | 第1轮/第20轮均可点找书，关闭书单继续原对话 | `mvp-p4` |
| P5 上线质量门禁 | `feat/p5-release-hardening` | 性能/安全/隐私、投诉处理、部署、备份恢复、变更回滚、法定手续核对 | 集成测试、类型检查、迁移/备份恢复、压力/故障演练 | 上线清单与必要监管手续完成后才公测 | `mvp-rc1` |

**P1→P2 的纵向切片**：P1 允许注入 Mock `RecommendationPort`，但 P2 替换时不得修改前端已经批准的意图和书单数据结构。**P3 不依赖 P2**：即使 P2 推荐服务故障，也能独立演示思辨对话。

## D. 单阶段 Git / PR 流程

首次操作：

```bash
git init -b main
git add .
git commit -m "chore: initialize wenyushu specifications"
git remote add origin <YOUR_GITHUB_REMOTE>
git push -u origin main
```

对于已经存在的仓库，禁止再次 `git init` 和随意覆盖 remote。

每阶段开始：

```bash
git switch main
git pull --ff-only origin main
git switch -c feat/p1-daily-exploration
```

Codex 在 feature branch 上修改代码，完成后至少执行：

```bash
# 由 P0 建立跨平台任务脚本，以下命令是目标接口
python -m pytest backend/tests
# 在 web/ 中运行
npm run lint
npm run typecheck
npm run build
# 从空库执行 Alembic 升级并验证约束
# 运行 OpenAPI 契约检查与场景集成测试
```

提交、建立 PR（示例）：

```bash
git status --short
git add backend web contracts docs db infra .github
# 第一个阶段若有这些目录尚未创建，应只 add 实际存在且确认的路径
git commit -m "feat(exploration): implement daily question flow"
git push -u origin feat/p1-daily-exploration
# 可用 GitHub CLI：gh pr create --base main --head feat/p1-daily-exploration
```

合并前：

- CI 必须全部成功（Backend tests/lint/migrations, Frontend lint/typecheck/build, API schema consistency）。
- 人工检查页面交互和失败情形；在 `docs/acceptance/P1.md` 保存验收内容并纳入该 PR。
- 检查新增表/字段是否有 Alembic 迁移；OpenAPI、DTO、测试是否同步。
- 检查 `git diff` 没有泄漏 `.env`、密钥、用户原始对话或大型生成文件。
- PR 描述说明：本次范围、改动模块、API/DB 变更、执行命令与测试结果、风险与回滚方式。

人工验收、CI 均通过后合并 PR，然后本地同步主线并打里程碑：

```bash
git switch main
git pull --ff-only origin main
git tag -a mvp-p1 -m "P1 daily exploration accepted"
git push origin mvp-p1
```

修复 bug 时：创建 `fix/<scope>` 分支 → PR → CI/验收 → 合并；**不要随意 `git reset --hard`、`push --force` 或直接修改 main**。需要回退时优先 `git revert` 已合并提交；涉及数据库迁移须先确认可回滚/前向修复方案。

## E. GitHub 设置建议

- `main` 受保护：禁止 force push、要求 PR、至少必需 CI checks 成功。
- 有协作者时启用至少一位 reviewer；如果只有一个仓库维护者，不能凭空要求他人审批，自己人工验收加自动检查，条件允许再找独立审阅者。
- PR 小而完整，**单一阶段/有限范围**；避免多个 Codex 会话在同一工作树同时大改相同文件。
- 推荐 `squash merge` 保持清晰的主线，一个 PR 一个可阅读的主提交；阶段 `tag` 便于对照验收版本。
- CI 测试数据库使用隔离的临时 PostgreSQL；Mock 外部 LLM/Search，不要求 PR 上传真实 DeepSeek Key。

官方： https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches

## F. 验收记录模板（每阶段复制）

本次有限范围补充“思辨助手体验与观点收藏”单独验收，不视为后续推荐/检索阶段完成。范围与测试证据见 [验收记录](acceptance/DISCUSSION_VIEWPOINTS.md)、[真实模型试答](acceptance/DISCUSSION_QUALITY.md) 和 [ADR-014](adr/014-discussion-viewpoints.md)。需检查消息原文/AI提炼的来源区分、刷新持久化、返回原消息、跨身份隔离、提炼幂等及失败恢复、删除原会话的隐私清理；仍须CI和人工产品验收后另行授权合并。

```markdown
# Pn 验收记录
- PR：
- 提交 SHA：
- 执行人 / 日期：
- 本阶段功能清单：
- 自动化命令与输出摘要：
- 手工测试（操作→预期→实际）：
- 失败/回归用例：
- 数据库迁移情况：
- OpenAPI 契约变动：
- 安全与隐私检查：
- 截图/演示（如适用）：
- 回滚方案：
- 结论：PASS / FAIL
```

**只允许验收记录 PASS 的阶段合并并打 Tag。**

## G. 如何给 Codex 下达每阶段任务

复制 `docs/CODEX_START.md` 的模板，指定阶段与 Tag。仅写目标、操作、约束、验收、必要输出；不得同时要求后续阶段功能。完成必须停在 PR 等待人工验收，不得自称已经上线。
