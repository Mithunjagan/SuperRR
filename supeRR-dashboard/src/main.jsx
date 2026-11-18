import React from "react";
import { createRoot } from "react-dom/client";
import { Analytics } from "@vercel/analytics/react";

// Load starter CSS before App traverses authored component stylesheet imports.
import "./theme.css";
import "./styles.css";
import "./theme-picker.css";
import "./source-preview.css";
import "./content/dashboard/dashboard.css";
import "./content/report/report.css";
import "./print.css";
import "./theme-runtime.js";
import { App } from "./App.jsx";
import reviewedSnapshot from "./data.json";

const hosted = globalThis.location?.hostname.endsWith(".chatgpt.site") ?? false;
const splitViewer = import.meta.env.MODE === "viewer";

function openOverviewOnReload() {
  if (hosted || performance.getEntriesByType("navigation")[0]?.type !== "reload") return;

  const { history, location } = window;
  const previousRestoration = history.scrollRestoration;
  history.scrollRestoration = "manual";
  if (location.hash) {
    const url = new URL(location.href);
    url.hash = "";
    history.replaceState(history.state, "", url);
  }
  window.scrollTo({ top: 0, left: 0, behavior: "instant" });
  window.addEventListener("pageshow", () => {
    requestAnimationFrame(() => { history.scrollRestoration = previousRestoration; });
  }, { once: true });
}

async function loadViewerSnapshot() {
  const url = document.querySelector('meta[name="data-app-local-snapshot"]')?.content;
  if (!url) throw new Error("The dashboard snapshot is missing.");
  const response = await fetch(url);
  if (!response.ok) throw new Error("The dashboard snapshot could not be loaded.");
  return response.json();
}

async function mount(element) {
  const root = createRoot(element);
  try {
    const snapshot = splitViewer ? await loadViewerSnapshot() : reviewedSnapshot;
    document.title = snapshot.title || "SupeRR";
    root.render(
      <React.StrictMode>
        <App hosted={hosted} reviewedSnapshot={snapshot} />
        <Analytics />
      </React.StrictMode>,
    );
  } catch {
    root.render(<main className="dashboard-shell-loading-error" role="alert">The dashboard could not load. Refresh the page to try again.</main>);
  }
}

const element = globalThis.document?.getElementById("root");
if (element) {
  openOverviewOnReload();
  void mount(element);
}
