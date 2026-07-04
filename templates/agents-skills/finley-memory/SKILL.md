---
name: finley-memory
description: "跨会话记忆：一段工作收尾时运行 python .finley/scripts/add_session.py 把本次做了什么写进 journal；新会话开场主动读取 .finley/workspace/<开发者>/ 最近的 journal 以恢复上下文。用于结束一段实现工作、或刚开始新会话需要了解此前进展时。"
---

# Finley 记忆层

Finley 的记忆层参考 Trellis 的做法：**把「本次会话发生了什么」持久化到仓库里的 journal**，让下一次会话（无论是你还是队友）不必从零理解项目。

对话会被压缩，文件不会。经验、进展、坑，都落盘到 `.finley/workspace/<开发者>/`。

---

## 何时触发

- **会话开场（读）**：新会话开始、需要了解此前进展时——主动读取最近的 journal 恢复上下文。
- **工作收尾（写）**：完成一段实现 + 质量门禁通过后、准备结束这轮工作时——把这段会话写进 journal。

---

## 步骤 A：会话开场恢复上下文（读）

1. 确认当前开发者目录：`.finley/workspace/<开发者>/`（开发者标识来自 git user.name / 环境变量 `FINLEY_DEVELOPER` / `.finley/config.yaml` 的 `developer`）。
2. 先读该目录的 `index.md` 看「当前状态」和「会话历史」表，定位活跃的 journal 文件。
3. 读最近的 `journal-N.md` 里最后 1~2 个 Session，了解上次做到哪、有什么待办和坑。
4. 用这些上下文指导本次工作，避免重复劳动。

```bash
# 例：查看当前开发者的索引与最新 journal
cat .finley/workspace/*/index.md
```

## 步骤 B：工作收尾写 journal（写）

在一段工作（通常是一次 `/speckit.implement` + 门禁全绿）收尾时运行：

```bash
python .finley/scripts/add_session.py \
  --title "本次工作的标题" \
  --summary "一两句话总结做了什么、结论是什么" \
  --commit "abc1234,def5678"
```

要点：

- `--title` 必填；`--summary` 写清楚「做了什么 + 结果」。
- `--commit` 填本次相关的 commit 哈希（逗号分隔）；纯规划性会话可省略。
- 详细内容可用管道传入：`cat detail.md | python .finley/scripts/add_session.py --stdin --title "..."`。
- 开发者/分支默认自动探测，必要时用 `--developer` / `--branch` 覆盖。

脚本会把 Session 追加到 `journal-N.md`（超过 `journal.max_lines` 自动轮转到下一个），并更新 `index.md` 的会话历史表。

---

## 注意事项

- **只做手动收尾摘要**：Finley 记忆层不做会话开场的自动上下文汇总——恢复上下文靠你按「步骤 A」主动读 journal。
- **一段工作一条 Session**：不要把无关的多件事塞进一条；也不要每改一行就记一次。
- **个人 journal 独立**：按开发者分目录存放，天然避免团队冲突；共享的规范/规格才进公共目录评审。
- **与门禁配合**：推荐顺序是「实现 → `gate.py` 全绿 → `add_session.py` 收尾」。
