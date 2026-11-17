# SuperRR

Rajasthan Royals scouting analysis for SupeRR Selector Round 1. This project compares player performance under pressure, checks the robustness of the rankings, and explores auction scenarios.

- [Dashboard deployment](supeRR-vercel/README.md) covers Vercel setup and the server-side Gemini analyst.
- [Final scouting dossier](output/pdf/SupeRR_Round_1_Scouting_Dossier.pdf)
- [Unstop submission order](output/final_recheck/Unstop_Submission_Order.csv)
- [Final methodology and evidence](output/final_recheck/README.md)

For Vercel, set the project **Root Directory** to `supeRR-vercel` and configure `GEMINI_API_KEY` as a server-side environment variable. The deployed dashboard includes canned dossier answers that work without Gemini.

The analysis scripts expect an authorized local copy of the competition Data Pack. The repository includes aggregate results, reports, dashboard source and deployable assets. The source snapshot and authored dashboard components live in `supeRR-dashboard/src`. To rebuild them, start with the Codex Data dashboard scaffold and replace its authored components, snapshot and theme with these files. Vercel serves the precompiled files in `supeRR-vercel/public`.
