# 问与书 · Codex 架构与开发交付包

版本：SAD 1.0 / 2026-10-24

## P0 本地运行

当前已增加基础工程；实际验收状态见 `docs/acceptance/P0.md`。以下原交付包说明保留作基线背景。

前置：Python 3.13、Docker Desktop（Linux containers，Compose v2）。不需要 DeepSeek Key。

```powershell
python scripts/dev.py up
```

浏览器访问 http://localhost:3000。首次启动自动在 `.local/compose.env` 创建随机密码及 CSRF 密钥；重启复用，不打印凭证。该目录被 Git 忽略。请使用 localhost，不使用局域网 IP；默认仅绑定回环地址。

```powershell
python scripts/dev.py status
python scripts/dev.py logs
python scripts/dev.py down
```

停止保留数据库卷；不要添加 `down -v`。数据库只在 Compose 内网开放。独立 migrate 服务成功后才启动 API/Worker。

P0 仅开放 `/api/v1/auth/anonymous-session`（POST/DELETE）和 `/api/v1/health/live`、`/api/v1/health/ready`。`/openapi.json` 为运行时接口描述；P1—P5 业务接口尚未注册。

### 开发与检查

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r backend/requirements.lock
.\.venv\Scripts\ruff check backend
.\.venv\Scripts\ruff format --check backend
.\.venv\Scripts\python scripts/validate_contract.py
.\.venv\Scripts\python -m pytest backend/tests -q
cd web
npm ci
npm run api:generate
npm run lint
npm run typecheck
npm run build
```

数据库集成测试必须设置 `TEST_DATABASE_URL`，指向**隔离、空的、名称以 `_test` 结尾**的 PostgreSQL 数据库。测试会创建并移除本项目 schema，最后验证升级/降级；不要指向任何实际使用的库。没有配置时会明确 skip，不计为数据库验收通过。

```powershell
$env:TEST_DATABASE_URL='postgresql+psycopg://USER:PASSWORD@localhost:5432/wenyushu_test'
.\.venv\Scripts\python -m pytest backend/tests -q
```

使用外部开发库时，设置 `DATABASE_URL`、至少 32 字符的随机 `CSRF_SECRET`、JSON 格式的 `ALLOWED_ORIGINS`，从根目录运行：

```powershell
$env:PYTHONPATH='backend'
.\.venv\Scripts\alembic -c backend/alembic.ini upgrade head
.\.venv\Scripts\uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8000 --no-access-log
# 另一终端，复用相同配置
.\.venv\Scripts\python -m app.worker
# web/ 下，独立终端
npm run build
npm run start
```

API 内部地址默认 `http://127.0.0.1:8000`；Compose 构建为 `http://api:8000`。前端只请求同源 `/api/v1`，不接触服务器密钥。

服务启动后，在 web/ 执行 `npx playwright install chromium` 和 `npm run test:e2e`。测试真实首页、Secure/HttpOnly Cookie、两个浏览器身份隔离、刷新、失败重试与 390/1440px 布局。远程访问必须使用 HTTPS；不通过关闭 Secure 适配不安全来源。

### 分层与验收

参见 `docs/P0_ARCHITECTURE.md` 的依赖和数据流说明，以及 `docs/acceptance/P0.md` 的命令证据、手工验收与限制。每阶段经 CI 和用户验收后才合并；本阶段不部署生产。

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
