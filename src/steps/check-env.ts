import { commandExists, tryOutput } from "../utils/exec.js";
import { log } from "../utils/logger.js";
import pc from "picocolors";

interface CheckResult {
  ok: boolean;
  label: string;
  detail: string;
  /** 安装 / 修复指引（失败时展示）。 */
  hint: string;
}

function parseMajor(version: string | null): number | null {
  if (!version) return null;
  const m = version.match(/(\d+)\.(\d+)(?:\.(\d+))?/);
  return m ? Number(m[1]) : null;
}

function parseMinor(version: string | null): [number, number] | null {
  if (!version) return null;
  const m = version.match(/(\d+)\.(\d+)/);
  return m ? [Number(m[1]), Number(m[2])] : null;
}

async function checkNode(): Promise<CheckResult> {
  const major = parseMajor(process.version);
  const ok = major !== null && major >= 18;
  return {
    ok,
    label: "Node.js ≥ 18",
    detail: process.version,
    hint:
      "请安装 Node.js 18 或更高版本：https://nodejs.org/ （推荐用 nvm/fnm 管理版本）。",
  };
}

async function checkGit(): Promise<CheckResult> {
  const has = await commandExists("git");
  const ver = has ? await tryOutput("git", ["--version"]) : null;
  return {
    ok: has,
    label: "Git",
    detail: ver ?? "未安装",
    hint: "请安装 Git：https://git-scm.com/downloads",
  };
}

async function checkPython(): Promise<CheckResult> {
  // 优先 python3，其次 python
  const bin = (await commandExists("python3"))
    ? "python3"
    : (await commandExists("python"))
      ? "python"
      : null;
  const ver = bin ? await tryOutput(bin, ["--version"]) : null;
  const mm = parseMinor(ver);
  const ok = mm !== null && (mm[0] > 3 || (mm[0] === 3 && mm[1] >= 11));
  return {
    ok,
    label: "Python ≥ 3.11",
    detail: ver ?? "未安装",
    hint:
      "请安装 Python 3.11 或更高版本：https://www.python.org/downloads/ 。\n" +
      "    门禁与记忆脚本用纯标准库（tomllib）实现，需 3.11+。",
  };
}

async function checkUv(): Promise<CheckResult> {
  const has = await commandExists("uv");
  const ver = has ? await tryOutput("uv", ["--version"]) : null;
  return {
    ok: has,
    label: "uv（spec-kit 依赖）",
    detail: ver ?? "未安装",
    hint:
      "spec-kit 通过 uv 安装与运行。请安装 uv：\n" +
      "    macOS/Linux: curl -LsSf https://astral.sh/uv/install.sh | sh\n" +
      "    或见 https://docs.astral.sh/uv/",
  };
}

export interface SpecifyStatus {
  available: boolean;
  version: string | null;
}

/** 单独检测 specify CLI（缺失不阻断硬性环境，但会给出安装指引）。 */
export async function checkSpecify(): Promise<SpecifyStatus> {
  const available = await commandExists("specify");
  const version = available ? await tryOutput("specify", ["--version"]) : null;
  return { available, version };
}

/**
 * 环境检测：Node/Git/Python/uv 为硬性依赖，任一缺失则阻断初始化并打印
 * 清晰的中文安装指引，随后由调用方非零退出。
 * 返回是否全部通过。
 */
export async function checkEnv(): Promise<boolean> {
  log.step("步骤 1/4：环境检测");

  const checks = await Promise.all([
    checkNode(),
    checkGit(),
    checkPython(),
    checkUv(),
  ]);

  for (const c of checks) {
    if (c.ok) {
      log.success(`${c.label} — ${pc.dim(c.detail)}`);
    } else {
      log.error(`${c.label} — ${pc.dim(c.detail)}`);
    }
  }

  const failed = checks.filter((c) => !c.ok);
  if (failed.length > 0) {
    console.log();
    log.error(`环境检测未通过：缺少 ${failed.length} 项必需依赖。`);
    console.log(pc.bold("\n请先安装以下依赖后重试：\n"));
    for (const c of failed) {
      console.log(`${pc.red("•")} ${pc.bold(c.label)}`);
      console.log(`    ${c.hint}\n`);
    }
    return false;
  }

  // specify CLI 检测（软性：缺失给指引，由调用方决定是否继续）
  const specify = await checkSpecify();
  if (specify.available) {
    log.success(`specify CLI — ${pc.dim(specify.version ?? "已安装")}`);
  } else {
    log.warn("未检测到 spec-kit 的 specify CLI。");
    console.log(
      pc.dim(
        "    可用 uv 安装（替换 <tag> 为最新版本，如 v0.12.4）：\n" +
          "    uv tool install specify-cli --from git+https://github.com/github/spec-kit.git@<tag>\n" +
          "    安装后重跑 ai-init init 即可自动编排 spec-kit。",
      ),
    );
  }

  return true;
}
