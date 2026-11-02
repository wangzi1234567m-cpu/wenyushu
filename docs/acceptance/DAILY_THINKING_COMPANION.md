# 每日一问：案例推进、双向反问与思考同行

日期：2026-11-01。分支 `codex/daily-debate-dialogue`，基于观点收藏PR #5的 `2fdb3e948f191bc7f2c3addf915be4ce324436c7`。上游未合并，本PR仅展示本轮有限差异，不进入推荐/检索阶段。最终PR、提交SHA与CI结果见交付回复及PR检查。

## 本次改动

- 用户原文行为基线：[DAILY_QUESTION_AI](../policies/DAILY_QUESTION_AI.md)，完整保留六部分要求。
- 后端 `discussion/application/policy.py` 增加daily-debate-v1：单一主要推进点，按需案例/反例、正面回答反问、尊重不确定及不再追问、可修订总结、主动阅读请求的四项线索。未核验的情境标假设，改变题设标对照，不编造新闻、引用或心理学机制。
- `discussion/application/service.py` 只按服务端已授权探索快照的question_version_id注入每日一问附加策略，恢复旧会话同样适用；不读取用户可提交的“模式”字段，不在ConversationRuntime植入每日规则。基础策略保留不强制问号结尾，同时允许以检验前提而非仅澄清信息的方式提问。
- 前端 `features/discussion/panel.tsx` 增加“用案例继续”“我想反问”草稿入口、提示与输入说明，配合 `app/globals.css` 小范围样式。只填输入框，不自动发送；非空草稿时禁用，避免覆盖用户文字；共用讨论组件在返回原讨论时也保留入口。
- `backend/tests/test_discussion.py` 验证模型实际收到的上下文、原始立场/反问、非每日策略隔离、刷新和幂等重放不多调用。`web/tests/daily.spec.ts` 验证草稿可编辑、不自动发送、不覆盖现有输入、明确发送后持久化与刷新恢复。
- ADR-015、SAD、DELIVERY、行为基线、两份验收记录与两张运行截图同步。没有修改PRD、OpenAPI、DTO、数据库或任何历史消息/收藏数据。

## 数据流与契约

继续使用：选择立场/理由 → 探索快照 → DiscussionPolicy上下文 → 通用ConversationRuntime历史/摘要 → 已注入LLM → 现有SSE消息 → 保存与收藏。每次正常发送仍只走原消息调用，草稿按钮不联网、不额外生成问题。

总结“可修改”指用户在后续消息中要求修订、再手动收藏确认的回复；不是直接编辑旧消息/旧收藏，也不把AI总结冒充用户原话。用户不点击收藏不落收藏记录；原有按需结构化提炼不改。本轮不新增/放宽原文收藏接口。

阅读请求只在正常AI回复中整理“核心问题、明确观点、思想方向、阅读体验”，不是新建ReadingIntent或推荐任务；真实推荐、实际作品内容核验仍未实施，不以聊天文字冒充已检索或已核验。

## 实际执行命令与结果

```powershell
.venv\Scripts\ruff.exe check backend
.venv\Scripts\ruff.exe format --check backend
.venv\Scripts\python.exe scripts/validate_contract.py
$env:TEST_DATABASE_URL='postgresql+psycopg://postgres@127.0.0.1:55432/wenyushu_test'
.venv\Scripts\python.exe -m pytest backend/tests -q --tb=short
npm --prefix web run lint
npm --prefix web run typecheck
npm --prefix web run build
# 服务就绪、后端使用Mock时：
npm --prefix web run test:e2e
```

本机实际隔离PostgreSQL测试库，端到端使用独立Mock API8100及E2E_API_TARGET转发，不消耗真实模型；开发API8000仍读取现有.env。真实试答另用合成上下文、服务器现有模型配置调用，原文见[最终七轮试答](DAILY_THINKING_QUALITY.md)。

| 项目 | 结果 | 实际输出/观察 |
|---|---|---|
| Ruff与格式 | PASS | `All checks passed!` / `114 files already formatted` |
| OpenAPI契约 | PASS | `26 operations; 36 schemas; 283 resolved references`，本轮不变 |
| 后端/PG/架构/安全回归 | PASS | `72 passed, 2 warnings in 13.39s`，权限、CSRF、Origin、幂等、摘要与失败路径保持通过 |
| 前端lint/typecheck/build | PASS | ESLint/tsc退出0，Next构建成功 |
| 桌面/手机浏览器 | PASS | `26 passed (8.3s)`，包括新增草稿/反问完整路径 |
| 单一案例/必要时提问 | PASS（本次样本观察） | 最终开场214字，一个假设和一个问题；不是强制逐轮提问 |
| 用户反问直答与反例 | PASS（本次样本观察） | 实际先给判断和依据；反例明确改变条件，不要求用户改口 |
| 不确定/停止追问 | PASS（本次样本观察） | 用户说不要继续问后无问号，保留立场不确定；仍可能超软字数 |
| 总结与修订归属 | PASS（本次样本观察） | 用户与AI视角分开，新回复保留不确定、不自动保存；无原记录编辑 |
| 不主动推荐/仅用户要求阅读整理 | PASS（本次样本观察） | 最后一轮四项线索，无书单、无检索调用或成功声明 |
| 截图检查 | PASS | [1440px桌面](../screenshots/daily-thinking/desktop.png)、[390px手机](../screenshots/daily-thinking/mobile.png)，Mock合成输入，无私人历史 |
| 人工产品/语义验收 | 待用户验收 | 自动化只证明链路，七轮试答不保证所有模型回复质量 |

开发中新增测试首次插入位置错误，已修正；首次浏览器新增用例在开场尚未开始时就计数，误认为草稿触发了调用，现等待开场消息完成后再记录基数，保留“不自动调用”的断言。最终结果如上，未以重试隐藏失败。两条后端警告为既有Starlette/httpx测试适配弃用和本机pytest缓存写权限。

## 手工验收

沿用README启动方式，已构建情况下启动Next、从根目录读取.env启动API；不需要迁移（仍为0004）。

1. 进入 `/daily-question` 完成立场、理由选择，观察开场是否接住理由，以一个具体处境推进，而不是重复选边。
2. 点“用案例继续”：只填草稿，不出现新AI回复；改写再发送，检查案例标假设、论证边界。非空输入不能被快捷入口覆盖。
3. 点“我想反问”补全“现实里的打扮约会也是影响，有什么区别”，发送后AI应先回答，不把任务抛回来。
4. 要求反例并指出改变了题设，检查AI是否标注对照、承认局限；要求不要追问时不逼答。
5. 请求结束总结，再要求“保留我不确定所有影响是否都是控制”，检查用户/AI归属及修订。手动收藏修订版，刷新和来源恢复仍正常。
6. 主动要找书时仅整理上下文，当前页面与AI均诚实说明未开放检索；不发推荐请求。另一个匿名身份不可访问前者消息或收藏。

## 风险、迁移与回滚

无API/DTO/数据库变更，无新迁移，保留原有0004。策略按上下文动态追加，既有policy_version仍记录基础discussion-v2，额外daily-debate-v1不是数据库版本变更。

模型仍可能举例失当、过度概括或超过软字数；最终暂停回复226字，略超100—200软指导，不能称严格字数验收。没有真实案例检索核验，不能保证每条经验性表述准确；争论的有效性和温度仍须用户评价。不提供评分、胜负、双Agent或硬性轮换，不新增自动推荐。

回滚撤销本PR提交并重启后端、重新构建前端；不用降级数据库，不清空历史/收藏，不删除卷。本机页面与ready检查需再次确认200；CI和人工验收后另行授权合并main，当前不打Tag、不部署生产。
