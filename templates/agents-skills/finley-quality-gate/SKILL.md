---
name: finley-quality-gate
description: "强制质量门禁：在 /speckit.implement 写完代码后、提交前，必须运行 python .finley/scripts/gate.py 跑 lint/typecheck/test，红则修复再跑，直至全绿。用于任何写完或改完代码、准备结束一段实现工作或提交之前。"
---

# Finley 质量门禁

这是 Finley 工作流里**不可跳过**的一道关卡。它保证「写完的代码在提交前一定跑过 lint / typecheck / test」。

---

## 何时触发

只要满足以下任一情况，就必须执行本 skill：

- 刚用 `/speckit.implement` 执行完一批任务、代码已落盘；
- 手动改完任意源码、准备结束这段实现工作；
- 准备 `git commit` / 发起提交之前。

> 原则：**没跑过 `gate.py` 且全绿，就不算「实现完成」，更不允许提交。**

---

## 步骤

### 1. 运行门禁

在项目根目录执行：

```bash
python .finley/scripts/gate.py
```

它会：

1. 读取 `.finley/config.yaml` 的 `quality.frontend` / `quality.backend` 命令；
2. 对占位命令自动探测（前端读 `package.json` 的 scripts，后端读 `pyproject.toml`）；
3. 逐条运行 lint / typecheck / test，并在末尾聚合「通过 / 失败」清单。

### 2. 判读结果

- **全绿**（退出码 0）：门禁通过，可以继续收尾 / 提交。
- **有红项**（退出码 1）：按输出里列出的失败项定位问题。
- **未解析到命令**（退出码 2）：说明门禁尚未配置——去 `.finley/config.yaml` 填入真实命令，或确认 `package.json` / `pyproject.toml` 里有可被探测的脚本，然后重跑。**不要因为"没有命令"就当作通过。**

### 3. 修复后重跑

若有失败：**先修复代码，再重新运行 `gate.py`**，如此循环，直到全部通过为止。不要用注释、跳过测试、放宽类型等方式绕过门禁。

### 4. 记录（可选）

门禁通过后，若这段工作到此收尾，按 `finley-memory` skill 运行 `add_session.py` 写 journal。

---

## 注意事项

- **只增不减**：不要为了让门禁变绿而删除/禁用已有的 lint 规则、类型检查或测试。
- **占位不等于通过**：`.finley/config.yaml` 里形如 `<占位: ...>` 的命令会触发自动探测；探测不到时门禁会以退出码 2 失败，提醒你去配置。
- **前后端分离**：只想跑一侧时用 `--only frontend` 或 `--only backend`；但**提交前应跑全部**。
- **想先看会跑什么**：用 `python .finley/scripts/gate.py --dry-run` 预览命令而不执行。
- 门禁失败时进程会非零退出，CI / 提交前钩子可据此阻断。
