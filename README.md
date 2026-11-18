# SuperRR

Rajasthan Royals scouting analysis for SupeRR Selector Round 1. This project compares player performance under pressure, checks the robustness of the rankings, and explores auction scenarios.

- [Dashboard deployment](supeRR-vercel/README.md) covers Vercel setup and the local build.
- [Final scouting dossier](output/pdf/SupeRR_Round_1_Scouting_Dossier.pdf)
- [Unstop submission order](output/final_recheck/Unstop_Submission_Order.csv)
- [Final methodology and evidence](output/final_recheck/README.md)

For Vercel, set the project **Root Directory** to `supeRR-vercel`. Dossier Q&A runs directly in the dashboard.

The analysis scripts expect an authorized local copy of the competition Data Pack. The repository includes aggregate results, reports, dashboard source and deployable assets. The source snapshot and dashboard components live in `supeRR-dashboard/src`. Vercel serves the compiled files in `supeRR-vercel/public`.
