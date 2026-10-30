# ADR-014：共同思考式讨论与私有观点收藏

- 日期：2026-10-30。
- 状态：按用户本次明确提出的讨论优化、持久化观点收藏任务实施；新增向后兼容契约，不改变既有会话/推荐接口。
- 范围：discussion/conversation 授权读取端口、收藏存储、对话/收藏前端；不实现书籍检索、公开分享或知识管理系统。

## 决策与模块边界

DiscussionPolicy 改为共同思考：优先回应实质内容，辨析概念、推演理由、表达有依据的不同意见；不规定每轮提问或固定回复模板。上下文显式区分背景、已确认历史与用户最新表达，简短回应不被解读为必须继续逼问。保留最近历史、原文及滚动摘要。

收藏与提炼由现有 discussion 唯一负责，不新建重复业务模块；ConversationRuntime 只增加通用、鉴权的消息/快照读取能力，不依赖收藏、推荐或书目。API 不直接访问仓储。

原始消息通过服务端消息ID读取、确认归属与completed状态后逐字保存。source_type 区分 user_quote / ai_viewpoint / ai_summary；AI提炼永远标ai_summary，不冒称用户原话。客户端不能提交任意内容、actor或来源类型伪造原话。

提炼由用户点击“提炼最近讨论的观点”明确触发，读取最多20条已完成消息及题目背景，固定 up_to_seq。普通聊天不额外调用模型；每份快照只生成一次成功结果，允许0—3条，失败显式重试、并发409、缓存空结果。候选不自动收藏。每条必须引用快照中的真实消息ID，输出经Pydantic和安全端口校验。模型调用数、超时、单批重试有界。

## 数据与接口

Alembic 0004 创建 discussion.viewpoint_extractions（actor/conversation/up_to_seq唯一、状态、lease、尝试次数、结果JSON）和 discussion.saved_viewpoints（actor、来源、文本快照、原消息ID集合、话题、会话、收藏时间）。每张表Owner均为discussion；跨模块UUID不添加跨Owner外键。既有0001—0003不改。

新增 GET/POST /conversations/{conversation_id}/viewpoints、GET/POST /saved-viewpoints、DELETE /saved-viewpoints/{viewpoint_id}。POST收藏只接受原消息引用或已校验提炼结果的批次/序号，服务端生成稳定ID，重复点击不重复记录。分页、CSRF、Origin、匿名身份和统一错误沿用现有机制。

GET收藏返回来源可用状态，原讨论存在且可访问时允许返回相应消息；不可用时明确提示。显式删除原会话时，遵循SAD已有隐私清理规则，一并清理关联候选及收藏；取消收藏删除收藏快照，提炼缓存保留至原会话删除。不会在删除会话后隐性保留私密快照。

前端提供双方已完成消息的收藏入口、可选候选卡片和 /saved-viewpoints。收藏持久化在PostgreSQL，浏览器仅持有必要会话ID，不将观点或token存localStorage。原讨论通过 /discussion/{id}?message_id=... 恢复，不创建新会话或自动生成开场。

同步OpenAPI、设计DDL、ORM、迁移、DTO和测试。对话质量以真实A/B/C场景的人工审阅和实际输出记录为依据，Mock只验证机制，不能据提示词断言语义质量必然通过。

## 备选与回滚

不采用仅保存在浏览器的收藏，避免刷新丢失和来源混淆；不采用每轮自动提炼，避免延迟、费用及过量卡片。按需提炼是本次MVP选择，后续如引入自动候选需另行评估成本和质量。

回滚优先撤销应用提交并保留新增表与数据；旧版 readiness 只认0003，需要在回滚版本中兼容数据库0004后再切换流量。0004 downgrade 会删除全部收藏和提炼缓存，只在明确可丢弃的隔离测试库演练；不对开发或用户数据库直接降级，不删除数据卷。
