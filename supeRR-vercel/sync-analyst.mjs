import { copyFile, mkdir, readFile, writeFile } from "node:fs/promises";

// Keep both supported Vercel roots self-contained. Never import server code
// across the configured project root or expose it through the browser bundle.
const target = new URL("../supeRR-dashboard/src/content/server/", import.meta.url);
const source = await readFile(new URL("api/analyst.mjs", import.meta.url), "utf8");
const from = '"../server/analyst-evidence.json"';
if (!source.includes(from)) throw new Error("The analyst evidence import changed; review the dashboard adapter.");
await mkdir(target, { recursive: true });
await writeFile(new URL("analyst.mjs", target), source.replace(from, '"./analyst-evidence.json"').trimEnd() + "\n");
await copyFile(new URL("server/analyst-evidence.json", import.meta.url), new URL("analyst-evidence.json", target));
console.log("Analyst server bundle synchronized for the dashboard Vercel root.");
