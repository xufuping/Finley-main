import pc from "picocolors";

/** 统一的中文彩色日志输出。 */
export const log = {
  info(msg: string): void {
    console.log(`${pc.cyan("›")} ${msg}`);
  },
  step(msg: string): void {
    console.log(`\n${pc.bold(pc.cyan("▶"))} ${pc.bold(msg)}`);
  },
  success(msg: string): void {
    console.log(`${pc.green("✔")} ${msg}`);
  },
  warn(msg: string): void {
    console.warn(`${pc.yellow("⚠")} ${msg}`);
  },
  error(msg: string): void {
    console.error(`${pc.red("✗")} ${msg}`);
  },
  detail(msg: string): void {
    console.log(`  ${pc.dim(msg)}`);
  },
  title(msg: string): void {
    console.log(pc.bold(pc.magenta(msg)));
  },
};
