# @finleywdx/ai-init

> AI 工程化工作流初始化器 —— 一条命令，把「spec-kit 规范驱动开发 + 跨会话记忆层 + 质量门禁」铺进你的新项目。

`@finleywdx/ai-init` 提供命令行工具 `ai-init`。在你的新项目（如 Next.js）里运行它，它会：

1. **编排 [spec-kit](https://github.com/github/spec-kit)**：为 5 个主流 AI 编码 agent（Cursor、Claude、Codex、Gemini、Copilot）一次性安装 `/speckit.*` 系列命令，把「规范 → 计划 → 任务 → 实现」的规范驱动开发（SDD）流程带进项目。
2. **铺设 Finley 增量层**：一套轻量的 `.finley/` 质量门禁 + 记忆脚本（纯 Python 标准库实现，无第三方依赖）。
3. **写好 AI 助手说明**：在 `AGENTS.md` 里生成一个 Finley 工作流区块，告诉任意 AI 助手该怎么在本项目里干活。

## 它和 spec-kit 是什么关系？

spec-kit 负责**规范驱动开发的主流程**（constitution → specify → plan → tasks → implement）。`ai-init` 不重造这套流程，而是**编排调用** spec-kit 的 `specify` CLI 完成安装，再在其之上补两块 spec-kit 不覆盖的工程纪律：

- **质量门禁（Quality Gate）**：一条 `gate.py`，在提交前统一跑 lint / typecheck / test，强制「写完代码必须过门禁」。
- **记忆层（Memory）**：一套 `add_session.py` + journal，把「本次会话做了什么」持久化到仓库，让下次会话不必从零理解项目。

> 灵感来自 [Trellis](https://github.com/) 的「规范/任务/记忆搬进仓库」理念，但 Finley 只做最小可用的增量层，把主流程交给 spec-kit。

## 环境要求

运行 `ai-init init` 的机器需要具备（缺失会被检测并阻断，同时打印中文安装指引）：

| 依赖 | 版本 | 用途 |
| --- | --- | --- |
| Node.js | ≥ 18 | 运行本 CLI |
| Git | 任意近版 | 版本控制 / journal 分支探测 |
| Python | ≥ 3.11 | 运行 `gate.py` / `add_session.py`（需标准库 `tomllib`） |
| uv | 任意 | spec-kit 的安装与运行依赖 |

此外还需要 spec-kit 的 `specify` CLI。若未安装，`ai-init` 会给出用 uv 安装的指引（替换 `<tag>` 为最新版本，如 `v0.12.4`）：

```bash
uv tool install specify-cli --from git+https://github.com/github/spec-kit.git@<tag>
```

## 安装

在你的项目里作为开发依赖安装：

```bash
npm i -D @finleywdx/ai-init
```

或全局安装：

```bash
npm i -g @finleywdx/ai-init
```

也可以免安装直接用 npx：

```bash
npx @finleywdx/ai-init init
```

## 用法

在**目标项目根目录**运行：

```bash
ai-init init
```

它会依次执行：环境检测 → 编排 spec-kit → 铺设 `.finley/` → 合并 `AGENTS.md`。

### 常用选项

```bash
# 只安装指定的 spec-kit integration（逗号分隔）
ai-init init --integration cursor,claude

# 跳过 spec-kit 编排，只铺设 Finley 增量层
ai-init init --skip-speckit

# 只打印将执行的操作，不真正调用 specify、不写盘
ai-init init --dry-run

# 不向 specify 传 --ignore-agent-tools（默认会传，以免因未装某个 agent CLI 而失败）
ai-init init --no-ignore-agent-tools

ai-init --version
ai-init --help
```

> 关于多 integration：spec-kit 的 `specify init` 每次只接受**单个** `--integration`。`ai-init` 因此采用「首个 integration 用 `specify init .` 初始化，其余用 `specify integration install <name> --force` 逐个追加」的方式一次装齐 5 个 agent。

## 初始化后的目录

```text
你的项目/
├── .specify/                       # spec-kit 管理（规格 / 模板 / 记忆）
├── .cursor/ .claude/ ...           # 各 agent 的 /speckit.* 命令（spec-kit 生成）
├── .finley/
│   ├── config.yaml                 # 质量门禁命令映射 + 开发者/journal 配置
│   ├── scripts/
│   │   ├── gate.py                 # 质量门禁：lint / typecheck / test
│   │   └── add_session.py          # 记忆层：写 journal
│   └── workspace/<开发者>/         # 跨会话记忆 journal（自动生成）
├── .agents/skills/
│   ├── finley-quality-gate/SKILL.md
│   └── finley-memory/SKILL.md
└── AGENTS.md                       # 含 Finley 工作流区块
```

## 初始化后的日常工作流

1. **确立原则**：`/speckit.constitution` —— 定义代码质量、测试、UX、性能等治理原则。
2. **写规格**：`/speckit.specify` —— 描述「做什么 / 为什么」，先别谈技术栈。
3. **澄清**：`/speckit.clarify` —— 补齐规格里模糊的地方（建议在 plan 之前）。
4. **定方案**：`/speckit.plan` —— 给出技术栈与架构选择。
5. **拆任务**：`/speckit.tasks` —— 生成可执行的任务清单。
6. **一致性检查**：`/speckit.analyze` —— 跨规格/计划/任务做一致性与覆盖度检查（建议在 implement 之前）。
7. **实现**：`/speckit.implement` —— 按任务清单写代码。
8. **质量门禁（提交前强制）**：
   ```bash
   python .finley/scripts/gate.py
   ```
   有红项必须修复后重跑，直至全绿。门禁会读取 `.finley/config.yaml`，占位命令会自动从 `package.json` scripts（前端）与 `pyproject.toml`（后端 ruff/mypy/pytest）探测。
9. **收尾写 journal（记忆层）**：
   ```bash
   python .finley/scripts/add_session.py --title "本次工作标题" --summary "做了什么" --commit "abc1234"
   ```
   新会话开场时，主动读取 `.finley/workspace/<开发者>/` 里最近的 journal 恢复上下文。

> Codex CLI 的 skills 模式使用 `$speckit-*`；斜杠命令的确切形态以你所用 agent 平台为准。

## 配置 `.finley/config.yaml`

```yaml
quality:
  frontend:
    lint: "<占位: 前端 lint 命令，如 npm run lint>"
    typecheck: "<占位: 前端类型检查命令，如 npm run typecheck>"
    test: "<占位: 前端测试命令，如 npm test>"
  backend:
    lint: "<占位: 后端 lint 命令，如 ruff check .>"
    typecheck: "<占位: 后端类型检查命令，如 mypy .>"
    test: "<占位: 后端测试命令，如 pytest>"
developer: ""          # 留空则自动探测（FINLEY_DEVELOPER > git user.name > 系统用户名）
journal:
  max_lines: 2000      # journal 超过该行数自动轮转
```

- 值形如 `<占位: ...>` 时，`gate.py` 会尝试自动探测；你也可以随时替换成项目真实命令。
- 前端探测：`package.json` 的 `scripts` 里的 `lint` / `typecheck`(或 `type-check`) / `test`，并按锁文件选择 npm / pnpm / yarn / bun。
- 后端探测：`pyproject.toml` 里检测到 `ruff` → `ruff check .`；`mypy` → `mypy .`；`pytest` → `pytest`。

---

## 发布这个包到 npm（维护者向）

本仓库是 `@finleywdx/ai-init` 的源码。发布步骤：

```bash
# 1. 安装依赖
npm install

# 2. 构建（tsup 产物在 dist/；prepublishOnly 会在 publish 前自动 clean + build）
npm run build

# 3. 本地自检
node dist/cli.js --version
node dist/cli.js --help

# 4. 预览将要发布的文件清单
npm pack --dry-run

# 5. 登录 npm
npm login

# 6. 发布（scope 包默认私有，公开发布必须加 --access public）
npm publish --access public
```

发布内容由 `package.json` 的 `files` 白名单控制，仅包含 `dist/`、`templates/`、`README.md`、`LICENSE`。`bin` 字段把 `ai-init` 指向构建产物 `dist/cli.js`。

### 本地联调

```bash
npm run build
npm link              # 在本仓库
# 到另一个测试项目里：
npm link @finleywdx/ai-init
ai-init init --dry-run
```

## 许可证

[MIT](./LICENSE)
