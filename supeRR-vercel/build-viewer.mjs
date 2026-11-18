import { execFileSync } from "node:child_process";
import { createHash } from "node:crypto";
import { readFile, writeFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";

const project = new URL("../supeRR-dashboard/", import.meta.url);
const publicDir = new URL("./public/", import.meta.url);
const compiled = new URL("dist/index.html", project);
const options = { cwd: fileURLToPath(project), stdio: "inherit" };
const vite = fileURLToPath(new URL("node_modules/vite/bin/vite.js", project));
const sha256 = bytes => createHash("sha256").update(bytes).digest("hex");

execFileSync(process.execPath, ["scripts/verify-protected-runtime.mjs"], options);
execFileSync(process.execPath, [vite, "build"], options);
const offline = await readFile(compiled);
execFileSync(process.execPath, [vite, "build", "--mode", "viewer"], options);

const snapshot = await readFile(new URL("src/data.json", project));
const snapshotHash = sha256(snapshot);
const snapshotPath = `snapshot.${snapshotHash}.json`;
const head = `<meta name="data-app-local-snapshot" content="${snapshotPath}">\n<link rel="stylesheet" href="./viewer.css">`;
const built = await readFile(compiled, "utf8");
if (!built.includes("</head>")) throw new Error("The dashboard build has no closing head tag.");
const html = Buffer.from(built.replace("</head>", `${head}\n</head>`));
const manifest = {
  version: 1,
  kind: "vite-viewer-v1",
  html: { path: "index.html", sha256: sha256(html), bytes: html.length },
  snapshot: { path: snapshotPath, sha256: snapshotHash, bytes: snapshot.length },
  sourceSnapshotSha256: snapshotHash,
};

await writeFile(new URL(snapshotPath, publicDir), snapshot);
await writeFile(new URL(manifest.html.path, publicDir), html);
await writeFile(new URL("data-app-build.json", publicDir), JSON.stringify(manifest, null, 2) + "\n");
await writeFile(new URL("../output/SupeRR_Dashboard_Preview.html", import.meta.url), offline);
