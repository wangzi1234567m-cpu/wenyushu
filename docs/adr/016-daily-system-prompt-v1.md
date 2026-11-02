# ADR-016：接入用户指定的每日一问 System Prompt V1.0

- 日期：2026-11-02。
- 状态：按用户“这是每日一问的系统提示词，写入进去”明确要求实施。
- 范围：每日一问策略文本、装配选择与回归；无API、字段、迁移或前端变更。

## 决策

将用户十二部分原文完整保存在 `backend/app/modules/discussion/application/prompts/daily_question_v1.md`，作为唯一运行时文本来源。policy.py按UTF-8加载为DAILY_SYSTEM_PROMPT，版本标识daily-question-v1.0。文件随backend Docker COPY进入镜像，不依赖docs目录。

DiscussionPolicy根据服务端探索快照question_version_id选用该原文，附加独立的服务端安全/能力边界；不再叠加旧discussion-v2正文及daily-debate-v1，避免角色、节奏与字数规则冲突。非每日一问仍使用原DISCUSSION_PROMPT。现有会话恢复时使用当前策略，不改写历史、收藏或既有基础policy_version字段。

附加边界保留内容安全、可信指令与不可信背景区分、消息role归属、假设与事实区分、当前纯文本显示格式和手动收藏约束。用户原文第10节描述未来独立阅读联动责任；当前尚未开放真实检索/推荐/Handoff，边界明确禁止模型声称已执行，不新增业务调用。

不把原文压缩成开发者摘要，不同时维护docs与代码两个可编辑副本，不把提示词置于前端或加入请求DTO。文档链接直接指向后端规范文件。模型语义质量通过实际试答另记，不能由提示词存在和Mock测试推断。

## 回滚与验证

撤销本PR提交并重启API即可恢复旧策略，无数据库操作、无前端重建要求。测试捕获真正传给LLM的system内容，确保为完整V1.0加运行边界，非每日会话保留原策略，并回归历史/权限/幂等/数据库。CI Compose同时验证提示词文件随镜像可加载。验收见 `docs/acceptance/DAILY_SYSTEM_PROMPT_V1.md`。
