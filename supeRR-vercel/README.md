# SupeRR | Under Pressure

Interactive companion to the 17 November 2026 Round 1 scouting dossier. The two ten-player lists follow the exact Unstop submission order. The auction panel shows conditional role calls.

## Deploy to Vercel

1. Extract this ZIP into its own folder. Deploy from the folder that contains `vercel.json`, `api/` and `public/`. Use the **Other** framework preset if Vercel asks. The build is already compiled in `public/`.
2. Import this folder through a Git repository in Vercel, or run `npx vercel` from the extracted folder to link it to a Vercel project.
3. In the Vercel project, open **Settings → Environment Variables** and add `GEMINI_API_KEY` to **Production**. Add it to **Preview** too if you want to test there. The optional `GEMINI_MODEL` overrides the default `gemini-3.5-flash-lite`.
4. Deploy or redeploy after setting the key. For CLI production deployment, run `npx vercel --prod`. Open the production URL in a signed-out window and verify the dashboard and *Ask the Analyst* panel. The three prewritten dossier answers work without the key.

The Gemini endpoint is server-side. The browser sends only the entered question. The function passes the question and aggregate evidence to Gemini. The package contains aggregate findings and no raw delivery data. The endpoint has per-instance request limits. Those limits do not act as a project-wide usage cap.

Vercel references
- https://vercel.com/docs/cli/deploy
- https://vercel.com/docs/environment-variables

## Preview the dashboard locally

From this folder run `python -m http.server 8080 --directory public` and open http://127.0.0.1:8080. For a local preview that includes the Gemini function, use `npx vercel dev` with a configured key.

