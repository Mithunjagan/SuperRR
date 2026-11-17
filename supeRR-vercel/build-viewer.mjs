import { createHash } from "node:crypto";
import { copyFile, readFile, writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const builderPath = process.argv[2];
if (!builderPath) throw new Error("Pass the installed Data app builder's data-app-build.mjs path.");

const { buildPrebuiltDataApp } = await import(pathToFileURL(resolve(builderPath)));
const projectDir = fileURLToPath(new URL("../supeRR-dashboard/", import.meta.url));
const { htmlPath } = await buildPrebuiltDataApp({
  projectDir,
  separateData: true,
  staticDemo: true,
  check: true,
  onProgress: console.log,
});

const manifestName = "data-app-build.json";
const dist = new URL("../supeRR-dashboard/dist/", import.meta.url);
const output = new URL("./public/", import.meta.url);
const manifest = JSON.parse(await readFile(new URL(manifestName, dist), "utf8"));
const built = await readFile(htmlPath, "utf8");
if (!built.includes("</head>")) throw new Error("The dashboard build has no closing head tag.");
const html = built.replace("</head>", '<link rel="stylesheet" href="./viewer.css">\n</head>');
manifest.html.sha256 = createHash("sha256").update(html).digest("hex");
manifest.html.bytes = Buffer.byteLength(html);
await writeFile(new URL(manifest.html.path, output), html);
await copyFile(new URL(manifest.snapshot.path, dist), new URL(manifest.snapshot.path, output));
await writeFile(new URL(manifestName, output), JSON.stringify(manifest, null, 2) + "\n");
