# Codex 执行约束｜问与书

## 任务目标
严格按 `docs/PRD.md`、`docs/SAD.md`、`contracts/openapi.yaml`、`db/schema.sql` 与 `docs/DELIVERY.md` 分阶段实现中国大陆 Web MVP。仅实施当前阶段任务，不实现未指定的后续功能。

## 明确操作
1. 在 feature 分支工作，先阅读规范与当前阶段验收。
2. 输出有限改动计划与受影响模块，识别契约冲突后先停止并提出 ADR。
3. 按模块责任开发；接口/表变更同步修改 OpenAPI、Alembic、前后端 DTO 与测试。
4. 添加正常、失败、越权、幂等、边界测试；所有第三方调用必须可注入 Mock。
5. 实际运行测试，记录命令与结果；提供 changed files、接口/迁移说明、风险与回滚建议。
6. 形成 PR，待人工验收；未获授权不合并至 main，不打阶段完成 Tag，不进行生产部署。

## 强制约束
- `Discussion` 不依赖 Recommendation；按需 Handoff 是独立编排。
- `ConversationRuntime` 仅保留通用会话/消息/记忆/推流能力，未来大师对话通过策略扩展，不提前实现。
- 不引入 Redis、LangGraph、Mem0、图数据库、微服务、付款或公开社区，除非有批准 ADR。
- PostgreSQL 模块 owner 唯一；跨模块通过端口而非直接读写私表。
- 保证匿名会话权限、CSRF、限制请求规模、内容安全、日志脱敏；DeepSeek API Key 只能服务端读取。
- 未经实际来源核验不能标记书籍已核验；不虚构引文或版权授权。
- 不覆盖用户已有文件；不执行破坏性 Git 命令；不提交密钥、用户私密内容或生成缓存。
- 以 Alembic 为正式迁移来源，`db/schema.sql` 仅是设计参考，不重复运行建表。

## 验收与报告
每阶段必须具备本地启动方法、通过的自动化测试、手工验证步骤、错误场景、PR/提交 SHA。验收不通过不进入下一阶段。
