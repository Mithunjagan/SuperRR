# SupeRR | Under Pressure

Interactive companion to the 17 November 2026 Round 1 scouting dossier. The two ten-player lists follow the exact Unstop submission order. The auction panel shows conditional role calls.

## Deploy to Vercel

1. Extract this ZIP into its own folder. Deploy from the folder that contains `vercel.json`, `api/` and `public/`. Use the **Other** framework preset if Vercel asks. The build is already compiled in `public/`.
2. Import this folder through a Git repository in Vercel, or run `npx vercel` from the extracted folder to link it to a Vercel project.
3. For CLI production deployment, run `npx vercel --prod`. Open the production URL in a signed-out window and check the Analytics controls and Dossier Q&A.

The dashboard uses reviewed aggregate data and provides three built-in dossier answers. The package includes no raw delivery data.

The optional `/api/analyst` endpoint is available for direct API callers. Configure `GEMINI_API_KEY` on the server to enable custom answers and set `GEMINI_MODEL` to override the default model. After updating the endpoint or its evidence, run `node supeRR-vercel/sync-analyst.mjs` to sync the copy used when the Vercel Root Directory is `supeRR-dashboard`.

Vercel references
- https://vercel.com/docs/cli/deploy
- https://vercel.com/docs/environment-variables

## Preview the dashboard locally

From this folder run `python -m http.server 8080 --directory public` and open http://127.0.0.1:8080.

Install the locked dashboard dependencies with `npm --prefix supeRR-dashboard ci`. From the repository root, run `node supeRR-vercel/build-viewer.mjs` with Node 24. The build refreshes the HTML, reviewed snapshot, and manifest in `public/` and the standalone HTML preview in `output/`.

Run `node --test supeRR-vercel/tests/analyst.test.mjs` from the repository root to verify request validation, dossier fallbacks, provider failures, and request limits. These tests mock Gemini; they do not confirm a live provider connection. Incomplete or blocked provider responses are reported as unavailable, with a dossier answer where one is supported.

## Interactive scouting analytics

The analytics lab recalculates the worst leave-one-match-out rating as the shrinkage slider moves. It compares any two players within the same official ten-player role shortlist. The 60-ball setting exactly reproduces all 20 official ratings; other settings are sensitivity scenarios with frozen eligibility and match contributions. They do not replace the submission order. The match-contribution bars use supplied match-ID order and are not a chronological time series.

`python supeRR-vercel/prepare-analytics.py` regenerates the match aggregates in the reviewed snapshot from `output/final_recheck/`, asserting ratings, qualifying balls, and match counts. It sets the authoring state to `updating`; set `buildStatus` to `complete` after finishing and verifying changes, then rebuild. Run `node --test supeRR-vercel/tests/*.test.mjs` for all analyst and analytics checks.

Graphs update locally without an API round trip. The data remains the 17 November scouting snapshot. Scroll effects use one scheduled frame, authored-element style updates, and intersection observers; reduced-motion preferences disable animation. Content-addressed snapshot JSON is immutable-cacheable on Vercel. Browser rendering and deployed performance need verification on the actual destination; a successful build is not a frame-rate guarantee.

