# SupeRR leverage analysis evidence

This archive contains derived player-level and model-level tables and the code used to produce them. Place the original supplied Data Pack directory at the root beside the Python scripts. The six input hashes are recorded in output/leverage_analysis/results.json. The archive omits the supplied raw CSVs and the delivery-level reconstruction.

## Reproduce

Use Python 3.12, pandas, NumPy, and ReportLab for the optional PDF renderer.

    python output/leverage_analysis/run_analysis.py
    python output/leverage_analysis/audit_results.py
    python output/leverage_analysis/make_report.py

The first command writes delivery_audit.csv.gz locally for the independent reconciliation. It records pre-state, win probability, expected WPA, realized WPA, and both role residuals without reproducing the supplied files. The second command verifies source hashes, data grain, sample sizes, player point estimates, and primary intervals. It also adds three reliability rankings. The PDF has the main study results.

## Evidence files

| File | Contents |
| --- | --- |
| results.json | Input hashes, rolling sample sizes, metric definitions encoded as thresholds, diagnostics, pair comparisons and sensitivity summaries |
| wp_validation.csv | Chronological validation and 2026 holdout log loss, Brier score, AUC and 10-bin calibration error |
| calibration.csv | Predicted and observed outcomes for each probability bin |
| pressure_profile.csv | Delivery counts, leverage flags and average modeled and realized swings by innings, phase, format, year and tournament stage flag |
| pressure_scenarios.csv | Counts and leverage in predefined scoreboard scenarios |
| bowl_rankings.csv, bat_rankings.csv | All eligible ranking rows, comparison variants and conditional fixture intervals for the main slices |
| bowl_own_baseline.csv, bat_own_baseline.csv | High versus low leverage for each eligible player, paired fixture intervals, and approximate false-discovery adjustment |
| bowl_reliability.csv, bat_reliability.csv | Primary rates, lower-quartile bootstrap scores and worst one-fixture-deleted rates |
| reliability_checks.json | Top-ten overlap and leaders with stricter sample and reliability rules |
| bumrah_hosein.json | Head-to-head estimates, sample counts and conditional shared-fixture bootstrap on the full set of variants |

## Units and eligibility

Delivery-based win-probability changes and leverage are fractions in the local delivery audit. The player tables scale scores by 100 into percentage points of win probability per delivery. The own-baseline standardized rate sums adjusted WPA and divides it by total model leverage in that band before multiplying by 100. Main ranking eligibility requires 60 legal high-leverage balls in at least eight matches with legal exposure. It is separate from the less restrictive head-to-head comparisons. The word overall covers the supplied screened IPL and T20I sample, and all predictions use earlier-year fit data. The 2022 matches supply training history.

The expected outcome distribution is empirical and backed off across nested pre-ball state buckets. Format and inning are the broadest buckets. Batter or bowler historical quality is an additional bucket for the opposing player's baseline. Phase itself is absent from the leverage gate. Conditional intervals hold estimated probabilities, outcome kernels and thresholds fixed. Multiple leaderboard comparisons and blind selection of the largest point estimate can make apparent leaders unstable.

