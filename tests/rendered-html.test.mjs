import assert from "node:assert/strict";
import { access, readFile } from "node:fs/promises";
import test from "node:test";

const root = new URL("../", import.meta.url);

async function render() {
  const workerUrl = new URL("../dist/server/index.js", import.meta.url);
  workerUrl.searchParams.set("test", `${process.pid}-${Date.now()}`);
  const { default: worker } = await import(workerUrl.href);
  return worker.fetch(
    new Request("http://localhost/", { headers: { accept: "text/html" } }),
    { ASSETS: { fetch: async () => new Response("Not found", { status: 404 }) } },
    { waitUntil() {}, passThroughOnException() {} },
  );
}

test("server-renders the SignalFit workbench", async () => {
  const response = await render();
  assert.equal(response.status, 200);
  assert.match(response.headers.get("content-type") ?? "", /^text\/html\b/i);

  const html = await response.text();
  assert.match(html, /<title>SignalFit｜AI 岗位能力地图<\/title>/i);
  assert.match(html, /只看 AI 岗位/);
  assert.match(html, /SignalFit 只做 AI 相关岗位/);
  assert.match(html, /三个 AI 方向，一套证据口径/);
  assert.match(html, /沿着证据找差距/);
  assert.match(html, /使用 Coding Agent 一键启动/);
  assert.match(html, /OpenCode、Claude Code、Codex 都可以/);
  assert.match(html, /复制一键启动指令/);
  assert.match(html, /\.\/signalfit update/);
  assert.match(html, /每周检查是否过期/);
  assert.match(html, /提交 AI JD/);
  assert.match(html, /提交真实面经/);
  assert.match(html, /git clone https:\/\/github\.com\/SuperMikasa\/signalfit\.git/);
  assert.match(html, /读取 AGENTS\.md/);
  assert.match(html, /不要上传、复制或提交简历与生成结果/);
  assert.match(html, /Claude Code/);
  assert.match(html, /OpenCode/);
  assert.match(html, /AI 全栈 \/ Agent 工程/);
  assert.match(html, /透明，比一个神秘总分更重要/);
  assert.match(html, /MIT License/);
  assert.doesNotMatch(html, /codex-preview|react-loading-skeleton/i);
});

test("keeps public assets anonymous and open-source ready", async () => {
  const [page, example, packageJson, readme] = await Promise.all([
    readFile(new URL("../app/page.tsx", import.meta.url), "utf8"),
    readFile(new URL("../public/example-fit.json", import.meta.url), "utf8"),
    readFile(new URL("../package.json", import.meta.url), "utf8"),
    readFile(new URL("../README.md", import.meta.url), "utf8"),
  ]);

  const publicText = [page, example, readme].join("\n");
  assert.doesNotMatch(publicText, /\/Users\/|resume_path|candidate_name/i);
  assert.match(packageJson, /"name": "signalfit"/);
  assert.doesNotMatch(packageJson, /react-loading-skeleton/);
  await access(new URL("../LICENSE", import.meta.url));
  await assert.rejects(access(new URL("../app/_sites-preview", import.meta.url)));
  await access(root);
});
