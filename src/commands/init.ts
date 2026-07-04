import { checkEnv } from "../steps/check-env.js";
import { runSpeckit, DEFAULT_INTEGRATIONS } from "../steps/run-speckit.js";
import { scaffoldFinley } from "../steps/scaffold-finley.js";
import { log } from "../utils/logger.js";
import pc from "picocolors";

export interface InitOptions {
  cwd?: string;
  integrations?: string[];
  /** 跳过 spec-kit 编排（只铺 Finley 增量层）。 */
  skipSpeckit?: boolean;
  ignoreAgentTools?: boolean;
  dryRun?: boolean;
}

/**
 * `ai-init init` 主流程：编排 1→4。
 *   1. 环境检测（缺失则阻断并非零退出）
 *   2. 编排 spec-kit（循环逐个 integration）
 *   3. 铺设 Finley 增量层
 *   4. 合并 AGENTS.md
 */
export async function init(options: InitOptions = {}): Promise<number> {
  const cwd = options.cwd ?? process.cwd();
  const integrations = options.integrations?.length
    ? options.integrations
    : [...DEFAULT_INTEGRATIONS];

  log.title("\n🌱 Finley · AI 工程化工作流初始化器\n");
  log.info(`目标目录：${pc.bold(cwd)}`);
  if (options.dryRun) log.warn("dry-run 模式：不会真正调用 specify，也不会污染目录。");

  // 1. 环境检测 —— 硬性依赖缺失则阻断
  const envOk = await checkEnv();
  if (!envOk) {
    log.error("\n初始化已中止：请安装上面列出的依赖后重试。");
    return 1;
  }

  // 2. 编排 spec-kit
  let speckitSkipped = false;
  if (options.skipSpeckit) {
    log.step("步骤 2/4：编排 spec-kit");
    log.warn("已通过 --skip-speckit 跳过 spec-kit 编排。");
    speckitSkipped = true;
  } else {
    const res = await runSpeckit({
      cwd,
      integrations,
      ignoreAgentTools: options.ignoreAgentTools ?? true,
      dryRun: options.dryRun,
    });
    speckitSkipped = res.skipped;
  }

  // 3 + 4. 铺设 Finley 增量层并合并 AGENTS.md（dry-run 时也跳过写盘）
  if (options.dryRun) {
    log.step("步骤 3/4：铺设 Finley 增量层");
    log.warn("dry-run：跳过复制模板。");
    log.step("步骤 4/4：合并 AGENTS.md");
    log.warn("dry-run：跳过写入 AGENTS.md。");
  } else {
    scaffoldFinley({ cwd });
  }

  // 收尾报告
  console.log();
  log.title("✅ 初始化完成");
  printNextSteps(speckitSkipped);
  return 0;
}

function printNextSteps(speckitSkipped: boolean): void {
  console.log(pc.bold("\n接下来："));
  const lines: string[] = [];
  if (speckitSkipped) {
    lines.push(
      "先安装 spec-kit 后重跑以补全命令：",
      "  uv tool install specify-cli --from git+https://github.com/github/spec-kit.git@<tag>",
    );
  }
  lines.push(
    "编辑 .finley/config.yaml，把 quality 里的占位替换成项目真实命令（也可留给 gate.py 自动探测）。",
    "在 AI 助手里按 spec-kit 流程推进：",
    "  /speckit.constitution → /speckit.specify → /speckit.clarify → /speckit.plan →",
    "  /speckit.tasks → /speckit.analyze → /speckit.implement",
    "实现完成、提交前必须跑质量门禁：",
    "  python .finley/scripts/gate.py",
    "一段工作收尾时记录 journal：",
    "  python .finley/scripts/add_session.py --title \"...\" --summary \"...\"",
  );
  for (const l of lines) console.log(`  ${pc.cyan("›")} ${l}`);
  console.log(pc.dim("\n详见项目根目录的 AGENTS.md 与 .agents/skills/。"));
}
