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
  assert.match(html, /沿着证据找差距/);
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
