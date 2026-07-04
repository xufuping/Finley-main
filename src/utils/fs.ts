import { fileURLToPath } from "node:url";
import path from "node:path";
import fs from "node:fs";

/** 包内 templates 目录的绝对路径（相对于构建产物 dist/cli.js 在 ../templates）。 */
export function templatesDir(): string {
  return fileURLToPath(new URL("../templates", import.meta.url));
}

/** 读取包自身 package.json（用于 --version）。 */
export function readOwnPackageJson(): { version: string; name: string } {
  const pkgPath = fileURLToPath(new URL("../package.json", import.meta.url));
  const raw = fs.readFileSync(pkgPath, "utf-8");
  return JSON.parse(raw) as { version: string; name: string };
}

export interface CopyResult {
  created: string[];
  skipped: string[];
}

/**
 * 递归复制目录。默认不覆盖已存在文件（幂等、保护用户改动）。
 * 返回相对 destRoot 的 created / skipped 列表，便于打印。
 */
export function copyDir(
  srcDir: string,
  destDir: string,
  destRoot: string = destDir,
  result: CopyResult = { created: [], skipped: [] },
): CopyResult {
  fs.mkdirSync(destDir, { recursive: true });
  for (const entry of fs.readdirSync(srcDir, { withFileTypes: true })) {
    const srcPath = path.join(srcDir, entry.name);
    const destPath = path.join(destDir, entry.name);
    if (entry.isDirectory()) {
      copyDir(srcPath, destPath, destRoot, result);
    } else {
      const rel = path.relative(destRoot, destPath);
      if (fs.existsSync(destPath)) {
        result.skipped.push(rel);
      } else {
        fs.copyFileSync(srcPath, destPath);
        result.created.push(rel);
      }
    }
  }
  return result;
}

export function readText(filePath: string): string {
  return fs.readFileSync(filePath, "utf-8");
}

export function writeText(filePath: string, content: string): void {
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
  fs.writeFileSync(filePath, content, "utf-8");
}

export function exists(filePath: string): boolean {
  return fs.existsSync(filePath);
}
