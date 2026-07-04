<!-- FINLEY:START -->
# Finley 工作流（AI 工程化）

本项目由 [`@finleywdx/ai-init`](https://www.npmjs.com/package/@finleywdx/ai-init) 初始化，采用一套「spec-kit 规范驱动开发 + 质量门禁 + 跨会话记忆」的工作流。AI 助手在本项目工作时**必须遵循**下面的整体流程。

## 整体流程

1. **规范驱动开发（spec-kit）**：用 spec-kit 的斜杠命令按序推进，先想清楚「做什么/为什么」，再写代码：
   - `/speckit.constitution` → 确立项目原则
   - `/speckit.specify` → 写需求规格（不谈技术栈）
   - `/speckit.clarify` → 澄清模糊点（plan 之前推荐）
   - `/speckit.plan` → 定技术方案
   - `/speckit.tasks` → 拆解可执行任务
   - `/speckit.analyze` → 跨产物一致性检查（implement 之前推荐）
   - `/speckit.implement` → 按任务实现
   > Codex CLI 的 skills 模式用 `$speckit-*`；具体命令名以你的 agent 平台为准。

2. **质量门禁（提交前强制）**：`/speckit.implement` 写完代码后、提交前，**必须**运行：
   ```bash
   python .finley/scripts/gate.py
   ```
   它跑 lint / typecheck / test；有红项必须**修复后重跑**，直至全绿才算实现完成。详见 skill `finley-quality-gate`。

3. **收尾写 journal（记忆层）**：一段工作收尾时运行：
   ```bash
   python .finley/scripts/add_session.py --title "..." --summary "..." --commit "..."
   ```
   把本次进展写进 `.finley/workspace/<开发者>/`。**新会话开场**应主动读取该目录最近的 journal 恢复上下文。详见 skill `finley-memory`。

## 关键位置

- `.finley/config.yaml` — 质量门禁命令映射 + 开发者/journal 配置
- `.finley/scripts/gate.py` — 质量门禁脚本
- `.finley/scripts/add_session.py` — 记忆 journal 脚本
- `.finley/workspace/` — 按开发者存放的跨会话记忆 journal
- `.agents/skills/finley-quality-gate/` — 质量门禁 skill
- `.agents/skills/finley-memory/` — 记忆层 skill
- `.specify/` — spec-kit 自身的规格 / 模板 / 记忆（由 spec-kit 管理）

> 本区块由 Finley 管理：位于 FINLEY 起止标记之间的内容可能被后续 `ai-init` 更新覆盖；标记之外的内容会被保留。
<!-- FINLEY:END -->
