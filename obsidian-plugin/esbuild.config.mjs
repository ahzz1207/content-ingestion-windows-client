import esbuild from "esbuild";

const production = process.argv.includes("production");

await esbuild.build({
  entryPoints: ["main.ts"],
  bundle: true,
  external: ["obsidian", "electron", "@codemirror/state", "@codemirror/view", "fs", "node:fs/promises"],
  format: "cjs",
  target: "es2020",
  outfile: "main.js",
  sourcemap: !production,
  minify: production,
});
