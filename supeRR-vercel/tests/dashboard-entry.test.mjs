import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { test } from "node:test";
import handler from "../../supeRR-dashboard/api/analyst.mjs";

test("dashboard deployment carries the canonical analyst and evidence inside its root", async () => {
  const canonical = await readFile(new URL("../api/analyst.mjs", import.meta.url), "utf8");
  const deployed = await readFile(new URL("../../supeRR-dashboard/src/content/server/analyst.mjs", import.meta.url), "utf8");
  assert.equal(deployed, canonical.replace('"../server/analyst-evidence.json"', '"./analyst-evidence.json"').trimEnd() + "\n");
  const original = await readFile(new URL("../server/analyst-evidence.json", import.meta.url), "utf8");
  const evidence = await readFile(new URL("../../supeRR-dashboard/src/content/server/analyst-evidence.json", import.meta.url), "utf8");
  assert.equal(evidence, original);
});

test("dashboard API entry handles methods and dossier requests", async () => {
  const savedKey = process.env.GEMINI_API_KEY;
  delete process.env.GEMINI_API_KEY;
  const run = (method, question) => {
    const req = { method, headers: { "content-type": "application/json" }, body: { question } };
    const res = { headers: {}, setHeader(name,value) { this.headers[name]=value; }, status(code) { this.code=code;return this; }, json(data) {return {code:this.code,data,headers:this.headers};} };
    return handler(req,res);
  };
  try {
    const get = await run("GET");
    assert.equal(get.code,405);
    assert.equal(get.headers.Allow,"POST");
    const dossier = await run("POST","Why is Hosein #1?");
    assert.equal(dossier.code,200);
    assert.equal(dossier.data.source,"dossier");
    assert.equal((await run("POST","Hello")).code,503);
  } finally {
    if(savedKey===undefined) delete process.env.GEMINI_API_KEY;
    else process.env.GEMINI_API_KEY=savedKey;
  }
});
