import { execa, type Options } from "execa";

/** 检测某个命令是否存在于 PATH 中。 */
export async function commandExists(command: string): Promise<boolean> {
  const probe = process.platform === "win32" ? "where" : "which";
  try {
    await execa(probe, [command]);
    return true;
  } catch {
    return false;
  }
}

/** 运行命令并返回其 stdout（trim 后）；失败返回 null，不抛异常。 */
export async function tryOutput(
  command: string,
  args: string[] = [],
): Promise<string | null> {
  try {
    const { stdout } = await execa(command, args);
    return stdout.trim();
  } catch {
    return null;
  }
}

export interface RunResult {
  ok: boolean;
  exitCode: number | undefined;
  stdout: string;
  stderr: string;
}

/**
 * 运行一条命令，继承或捕获输出。永不抛异常——把失败信息封装进 RunResult，
 * 便于上层给出友好的中文报错，而不是静默吞掉。
 */
export async function run(
  command: string,
  args: string[] = [],
  options: Options = {},
): Promise<RunResult> {
  try {
    const result = await execa(command, args, { reject: false, ...options });
    return {
      ok: result.exitCode === 0,
      exitCode: result.exitCode,
      stdout: typeof result.stdout === "string" ? result.stdout : "",
      stderr: typeof result.stderr === "string" ? result.stderr : "",
    };
  } catch (err) {
    const e = err as { exitCode?: number; stdout?: string; stderr?: string; message?: string };
    return {
      ok: false,
      exitCode: e.exitCode,
      stdout: typeof e.stdout === "string" ? e.stdout : "",
      stderr: typeof e.stderr === "string" ? e.stderr : e.message ?? String(err),
    };
  }
}
