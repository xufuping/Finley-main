import { defineConfig } from "tsup";

export default defineConfig({
  entry: ["src/cli.ts"],
  format: ["esm"],
  target: "node18",
  platform: "node",
  outDir: "dist",
  clean: true,
  sourcemap: false,
  minify: false,
  // CLI 入口需要 shebang 才能被直接执行
  banner: {
    js: "#!/usr/bin/env node",
  },
});
