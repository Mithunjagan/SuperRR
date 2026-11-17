import assert from "node:assert/strict";
import { afterEach, beforeEach, test } from "node:test";

const originalFetch = globalThis.fetch;
const originalKey = process.env.GEMINI_API_KEY;
const originalModel = process.env.GEMINI_MODEL;
const customQuestion = "What does the dossier say about sample size?";
let handler;
let moduleId = 0;

beforeEach(async () => {
  delete process.env.GEMINI_API_KEY;
  delete process.env.GEMINI_MODEL;
  ({ default: handler } = await import(`../api/analyst.mjs?test=${++moduleId}`));
  globalThis.fetch = async () => { throw new Error("Unexpected provider request"); };
});

afterEach(() => {
  globalThis.fetch = originalFetch;
  for (const [name, value] of [["GEMINI_API_KEY", originalKey], ["GEMINI_MODEL", originalModel]]) {
    if (value === undefined) delete process.env[name];
    else process.env[name] = value;
  }
});

function ask(question = customQuestion, options = {}) {
  const req = {
    method: options.method ?? "POST",
    headers: { "content-type": "application/json", ...options.headers },
    body: Object.hasOwn(options, "body") ? options.body : { question },
  };
  const res = {
    headers: {},
    setHeader(name, value) { this.headers[name] = value; },
    status(code) { this.code = code; return this; },
    json(data) { return { code: this.code, data, headers: this.headers }; },
  };
  return handler(req, res);
}

test("rejects invalid requests before contacting the provider", async () => {
  const cases = [
    [{ method: "GET" }, 405],
    [{ headers: { "content-type": "text/plain" } }, 415],
    [{ headers: { "content-length": "4097" } }, 413],
    [{ body: "{invalid" }, 400],
    [{ body: null }, 400],
    [{ body: { question: 12 } }, 400],
    [{ body: { question: "   " } }, 400],
    [{ body: { question: "x".repeat(321) } }, 400],
  ];
  for (const [options, status] of cases) {
    const result = await ask(undefined, options);
    assert.equal(result.code, status);
    assert.equal(result.headers["Cache-Control"], "no-store");
  }
  assert.equal((await ask(undefined, { method: "GET" })).headers.Allow, "POST");
});

test("all supported dossier questions work without a provider key", async () => {
  for (const [question, evidence] of [
    ["Why is Hosein #1?", /22\.10 to 21\.66/],
    ["Who is the pace bid?", /Archer leaves/],
    ["Did it predict 2026?", /44\.69 vs 50\.43/],
    ["What is own-baseline lift?", /earlier ordinary adjusted rate/],
    ["What counts as pressure?", /31–60 balls remaining/],
  ]) {
    const result = await ask(question);
    assert.equal(result.code, 200);
    assert.equal(result.data.source, "dossier");
    assert.match(result.data.answer, evidence);
    assert.ok(result.data.notice);
  }
  const unavailable = await ask();
  assert.equal(unavailable.code, 503);
  assert.equal(unavailable.data.source, undefined);
});

test("sends grounded evidence server-side and returns only visible answer parts", async () => {
  process.env.GEMINI_API_KEY = "test-key";
  process.env.GEMINI_MODEL = "custom-model";
  globalThis.fetch = async (url, options) => {
    assert.match(url, /custom-model:generateContent$/);
    assert.equal(options.headers["x-goog-api-key"], "test-key");
    const body = JSON.parse(options.body);
    assert.match(body.systemInstruction.parts[0].text, /Reviewed JSON evidence/);
    assert.equal(body.contents[0].parts[0].text, customQuestion);
    assert.equal(options.body.includes("test-key"), false);
    assert.ok(options.signal instanceof AbortSignal);
    return Response.json({ candidates: [{ finishReason: "STOP", content: { parts: [
      { thought: true, text: "private reasoning" }, { text: "Evidence answer." },
    ] } }] });
  };
  const result = await ask(`  ${customQuestion}  `);
  assert.deepEqual(result.data, { answer: "Evidence answer.", source: "live" });
  assert.equal(result.headers["Cache-Control"], "no-store");
});

for (const [upstream, expected] of [[400, 503], [401, 503], [403, 503], [404, 503], [429, 429], [500, 502]]) {
  test(`provider ${upstream} preserves dossier fallback and reports custom-question failure`, async () => {
    process.env.GEMINI_API_KEY = "test-key";
    globalThis.fetch = async () => new Response("", { status: upstream });
    const custom = await ask();
    assert.equal(custom.code, expected);
    assert.ok(custom.data.error);
    if (expected === 429) assert.equal(custom.headers["Retry-After"], "60");
    const dossier = await ask("Why is Hosein #1?");
    assert.equal(dossier.code, 200);
    assert.equal(dossier.data.source, "dossier");
    assert.ok(dossier.data.notice);
  });
}

test("empty, malformed and thought-only replies do not become live answers", async () => {
  process.env.GEMINI_API_KEY = "test-key";
  for (const data of [null, {}, { candidates: [] }, { candidates: [{ finishReason: "STOP", content: { parts: [
    { thought: true, text: "reasoning" }, { text: "   " },
  ] } }] }]) {
    globalThis.fetch = async () => Response.json(data);
    const result = await ask();
    assert.equal(result.code, 502);
    assert.equal(result.data.source, undefined);
  }
  globalThis.fetch = async () => new Response("not JSON");
  assert.equal((await ask()).code, 502);
});

test("cut-off or blocked replies use fallback instead of claiming live success", async () => {
  process.env.GEMINI_API_KEY = "test-key";
  for (const finishReason of [undefined, "", "MAX_TOKENS", "SAFETY", "RECITATION", "OTHER"]) {
    globalThis.fetch = async () => Response.json({ candidates: [{
      finishReason, content: { parts: [{ text: "Partial answer" }] },
    }] });
    const headers = { "x-vercel-forwarded-for": `finish-${finishReason}` };
    const result = await ask(undefined, { headers });
    assert.equal(result.code, 502, finishReason);
    assert.equal(result.data.source, undefined);
    const dossier = await ask("Why is Hosein #1?", { headers });
    assert.equal(dossier.code, 200);
    assert.equal(dossier.data.source, "dossier");
  }
});

test("network and timeout failures retain fallback even for non-Error rejections", async () => {
  process.env.GEMINI_API_KEY = "test-key";
  for (const error of [new Error("network failed"), new DOMException("timeout", "TimeoutError"), null]) {
    globalThis.fetch = async () => { throw error; };
    assert.equal((await ask()).code, 502);
    assert.equal((await ask("Why is Hosein #1?")).data.source, "dossier");
  }
});

test("per-client quota stops provider calls and keeps dossier answers available", async () => {
  process.env.GEMINI_API_KEY = "test-key";
  let calls = 0;
  globalThis.fetch = async () => {
    calls++;
    return Response.json({ candidates: [{ finishReason: "STOP", content: { parts: [{ text: "Answer" }] } }] });
  };
  const headers = { "x-vercel-forwarded-for": "test-client" };
  for (let i = 0; i < 8; i++) assert.equal((await ask(undefined, { headers })).code, 200);
  const limited = await ask(undefined, { headers });
  assert.equal(limited.code, 429);
  assert.equal(limited.headers["Retry-After"], "60");
  assert.equal((await ask("Why is Hosein #1?", { headers })).data.source, "dossier");
  assert.equal(calls, 8);
});

test("instance quota bounds provider calls across different clients", async () => {
  process.env.GEMINI_API_KEY = "test-key";
  let calls = 0;
  globalThis.fetch = async () => {
    calls++;
    return Response.json({ candidates: [{ finishReason: "STOP", content: { parts: [{ text: "Answer" }] } }] });
  };
  for (let i = 0; i < 60; i++) {
    assert.equal((await ask(undefined, { headers: { "x-vercel-forwarded-for": `client-${i}` } })).code, 200);
  }
  assert.equal((await ask()).code, 429);
  assert.equal(calls, 60);
});
