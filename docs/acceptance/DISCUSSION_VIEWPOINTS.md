# 思辨助手体验优化与观点收藏验收

日期：2026-10-30。分支 `codex/discussion-insights`，基于已获人工视觉认可的首页提交 `c8516f64d20ea5bc02ece8dd9eda781edac1ba2b`。本次有限范围扩展，未实现检索、推荐书单、公开分享、自动分类或滑动式每日一问。PR、提交SHA和CI链接见PR及交付回复，人工产品验收仍待用户完成，不自动合并。

## 改动与数据流

- `discussion/application/policy.py`、`service.py`：集中discussion-v2策略；实质回应、概念辨析、推理边界及有依据的不同意见；允许完整观点结束，不固定提问或套话。简短输入降低负担，复杂观点才展开，不编造引用、用户动机或人格诊断。保留原有历史、滚动摘要与观点变化机制。
- `conversation/application/ports.py`、`service.py`、`infrastructure/repository.py`：通用鉴权消息快照，固定seq、完整消息对，排除未完成/失败回复。ConversationRuntime不依赖收藏实现或推荐。
- `discussion/application/viewpoints.py`、`infrastructure/viewpoints.py`、`models.py`：现有discussion模块内新增收藏用例、来源验证、持久化仓储与提炼缓存；bootstrap注入真实/Mock实现。
- `api/viewpoint_dto.py`、`api/v1/viewpoints.py`、`routes.py`：严格DTO和统一鉴权入口；同步OpenAPI与前端生成类型。
- `web/src/features/viewpoints/`、`features/discussion/panel.tsx`：双方消息原文收藏、可选提炼卡片、收藏/取消反馈；`/saved-viewpoints`提供分页、加载、空状态、错误重试和来源跳转；`/discussion/[conversation_id]`恢复原讨论并定位消息，不重新创建或触发开场。结束/过期会话只读。Header增加“我的收藏”。推荐占位页保留当前conversation返回路径。
- `0004_saved_viewpoints.py`、设计DDL、readiness、契约/数据库/浏览器测试、ADR-014、SAD、DELIVERY和本记录同步更新。完整逐文件清单可用 `git diff --name-only c8516f64d20ea5bc02ece8dd9eda781edac1ba2b HEAD` 查看。

完整文件清单见[改动文件](DISCUSSION_FILES.md)。数据流：消息ID或提炼批次引用 → identity/CSRF/Origin → discussion用例 → ConversationSnapshotReader确认归属和来源 → discussion自己的PG表 → DTO → 收藏状态。客户端不能提交actor、source_type或任意内容伪造用户原话。

## 数据与接口

`discussion.saved_viewpoints`：id、actor_id、conversation_id、message_id、source_message_ids、source_type、content、topic_title、created_at。来源严格区分用户原话 `user_quote`、AI消息原文 `ai_viewpoint`、AI提炼 `ai_summary`。按actor/时间/id索引，稳定ID防重复收藏；取消后再次收藏重新记录时间。

`discussion.viewpoint_extractions`：actor/conversation/up_to_seq唯一，status、lease_id、attempts、items和时间戳。快照最多20条完成消息，按完整消息对限制16KB输入，允许0—3个候选；引用必须为输入中的真实消息ID，内容和安全验证失败不落成功结果。所有表唯一Owner为discussion，无跨模块私表读写或外键。

| 接口（统一前缀 `/api/v1`） | 行为 |
|---|---|
| GET `/conversations/{conversation_id}/viewpoints` | 获取当前缓存；不调用模型 |
| POST 同上，`{up_to_seq}` | 用户按需提炼；同快照成功/空结果复用，处理中409，失败可显式重试 |
| GET `/saved-viewpoints?limit=20&offset=0` | 仅当前身份；可按conversation_id过滤 |
| POST `/saved-viewpoints` | conversation_id + message_id，或extraction_id/item_index；服务端取原文/已校验候选，幂等返回201 |
| DELETE `/saved-viewpoints/{viewpoint_id}` | 仅当前身份可取消，缺失或他人404 |

普通聊天无额外提炼调用。提炼45秒总超时，模型调用不超过30秒，每批最多3次，当前库UTC日累计actor20/全局200次；90秒租约防挂起状态，失败可重试，候选不自动收藏。预算依据缓存计数，清理会话会清理计数，不能当作生产计费总闸。

## 实际执行结果

本机使用PostgreSQL16原生进程；测试库名 `wenyushu_test`，与开发数据隔离，禁止SQLite替代。PowerShell命令均在项目根目录执行：

```powershell
.venv\Scripts\ruff.exe check backend
.venv\Scripts\ruff.exe format --check backend
.venv\Scripts\python.exe scripts/validate_contract.py
$env:TEST_DATABASE_URL='postgresql+psycopg://postgres@127.0.0.1:55432/wenyushu_test'
.venv\Scripts\python.exe -m pytest backend/tests -q --tb=short
npm --prefix web run lint
npm --prefix web run typecheck
npm --prefix web run build
# 前后端已启动，API为Mock时：
npm --prefix web run test:e2e
```

本机浏览器回归使用独立Mock API8100和测试转发夹具 `E2E_API_TARGET=http://127.0.0.1:8100`，避免消耗用户真实服务或更改8000配置。CI在Compose内默认Mock运行同一套测试。

| 项目 | 结果 | 实际输出/证据 |
|---|---|---|
| 后端lint/format | PASS | `All checks passed!` / `114 files already formatted` |
| OpenAPI | PASS | `26 operations; 36 schemas; 283 resolved references`；运行时路由/DTO一致性测试通过 |
| 后端与实际数据库 | PASS | `71 passed, 2 warnings in 16.67s`；空库迁移、重复升级、ORM等价、约束拒绝、越权、伪造来源、CSRF、Origin、并发、重复保存、清理与失败重试 |
| 前端lint/typecheck/build | PASS | ESLint、tsc退出0；Next构建成功，新增收藏/原讨论路由正常 |
| 浏览器桌面/手机 | PASS | 24 passed (10.8s)；1440px桌面与390px手机，收藏/取消/刷新/来源跳转/错误恢复/身份隔离；旧测试硬编码题目文案已修复 |
| 真实模型A/B/C | PASS（有限样本） | 187/206/201字符，均0问号，有实际观点输出；原文及局限见[质量记录](DISCUSSION_QUALITY.md) |
| 真实提炼和收藏链路 | PASS | 真实回复261字符、提炼2条候选、保存2条后刷新恢复，定位原消息；清理测试会话HTTP200 |
| 推荐与分层回归 | PASS | 未点击不发推荐请求；原入口往返保留历史；既有架构依赖测试通过，无Discussion→Recommendation依赖 |
| 人工视觉/产品验收 | 待验收 | 此次收藏与讨论变化需用户实测；此前首页认可不替代本次验收 |

两条后端警告为现有Starlette/httpx测试适配弃用提示及Windows pytest缓存写权限，不影响断言。真实模型试答不参与自动化CI；自动化测试全部注入Mock。首次浏览器复跑22通过、2误报的原因和修正已如实保留。Windows Docker引擎此前不可用，本次本机不冒充通过Compose；CI另行验证Linux Compose。

已检查[桌面截图](../screenshots/discussion-viewpoints/desktop.png)和[手机截图](../screenshots/discussion-viewpoints/mobile.png)：使用测试夹具的Mock内容，无私人讨论或密钥；窄屏导航、长观点文字和操作按钮均无横向溢出。

首次Linux Compose CI为23通过/1失败，定位为收藏后立刻跨页时，列表先于保存完成而读取。前端API模块现在只在内存记录未完成写请求，列表等其结束再查询；消息按钮显示保存中。保留立即跨页用例并主动注入750ms保存延迟，验证实际时序，未用测试重试掩盖问题。后端/前端CI首次均通过；修复后的完整CI结果见PR当前提交检查。

已检查[桌面截图](../screenshots/discussion-viewpoints/desktop.png)和[手机截图](../screenshots/discussion-viewpoints/mobile.png)：使用测试夹具的Mock内容，无私人讨论或密钥；窄屏导航、长观点文字和操作按钮均无横向溢出。

## 本地启动及手工复验

沿用README的 `python scripts/dev.py up`（Docker正常时）或原生PostgreSQL、Alembic、uvicorn和Next启动方式。先备份现有数据库，读取已有被忽略的.env配置；不重新生成或打印密钥。从根目录执行：

```powershell
$env:PYTHONPATH='backend'
.venv\Scripts\alembic.exe -c backend/alembic.ini upgrade head
.venv\Scripts\uvicorn.exe app.main:create_app --factory --host 127.0.0.1 --port 8000 --no-access-log
# 另一终端
npm --prefix web run start
```

1. 打开 `/daily-question` 完成立场/理由，输入A/B/C及立场改变，检查自然回应、上下文与不强制提问。
2. 收藏一条自己的话和AI原文，确认按钮变为已收藏；点击提炼，核对真实来源和“AI提炼·非用户原话”，手动收藏其中一条，普通发消息时不自动提炼。
3. 打开“我的收藏”，检查三类来源、主题/时间；刷新仍存在。点击返回原讨论，应高亮原消息且不产生新回复。找书往返保留这段讨论。
4. 取消收藏、刷新确认消失；另一个浏览器身份看不到前一个的内容。删除原会话后关联收藏清空；匿名身份过期/被清除后不能通过旧ID读取。
5. 模型超时或提炼失败应提示重试，不阻断聊天；断网加载收藏出现错误，恢复后重试；没有候选时明确空状态。

## 迁移、风险与回滚

0004仅新增两张表和一个索引；保留0001—0003，应用启动无create_all。测试从空库升级并比较21张表和ORM，实际CHECK拒绝非法来源、空文本、非法JSON数组及越界状态/次数；本机开发库已升级0004，未删除已有记录。

- 匿名收藏属于当前浏览器凭证，不具备账号同步或长期保存承诺；默认7天身份有效期，丢失Cookie无法找回。删除原讨论会清理收藏，不提供脱离原文永久保留的语义。
- 模型仍可能误读或写出普通、冗长的观点；引用ID只能证明可追溯，不能证明语义保真，用户需核对。三例试答不是全面质量评估；不承诺事实核验或严格字数。
- 分页为offset，列表同时增删时可能位移；删除后回第一页。提炼为同步有界调用，不新增Worker业务队列，进程中断可按租约重试。
- 回滚优先revert本PR应用提交并保留0004数据。旧readiness期望0003，回滚应用必须先兼容0004版本，或采用前向修复；不直接部署必然ready失败的旧版本。downgrade0003会删除收藏/缓存，仅可在明确可丢弃测试库演练，不降级用户数据库、不删除卷。未部署生产。
