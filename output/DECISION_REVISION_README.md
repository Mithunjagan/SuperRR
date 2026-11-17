# SupeRR decision revision - 15 November 2026

The revised PDF keeps the supplied-data Model A batting and bowling lists and changes the acquisition decision layer. It adds incumbent ratings, the same best-match rule for every target, A/B sensitivity, simple forecast baselines, and explicit uncertainty. This is a retrospective revision; no rule is represented as preregistered.

## Decisions

- Default acquisition order: overseas batting (Klaasen; Rinku as domestic fallback), then domestic spin upgrade (Varun).
- If Archer leaves, the uncovered powerplay/death role takes precedence: Hazlewood is the first replacement target.
- Iyer and Brevis both receive a watchlist designation because they leave the top ten after their best match is removed.
- No candidate is assumed released or registered for the 2027 auction. Priority tiers are not calibrated rupee valuations.
- Ineligible incumbents have missing scores, not zero scores. Ratings describe the scored situations, not overall cricket ability or expected future wins.

## Reproduce the revision

Use Python with pandas, numpy, reportlab and pypdf. Place the original supplied `Data Pack` folder next to the scripts, unchanged. Input hashes and runtime versions are in `output/revision_manifest.json`. The pack is not redistributed in this archive.

Run from the extracted project root:

```text
python build_decision_audit.py
python render_scouting_dossier.py --external-validation output/cross_league --output output/pdf/SupeRR_Round_1_Scouting_Dossier.pdf
```

The archive includes the existing ranking/validation outputs and public-league evidence needed by these commands. Rebuilding all external evidence additionally requires the Cricsheet raw archives described in `output/cross_league/README.md`; raw public archives are not included here.

`build_decision_audit.py` recreates full-cohort A ratings from deliveries, asserts that both top tens agree with the submitted lists, derives B using the development-selected 240-ball ordinary prior, and calculates incumbent margins under four specifications. Candidate-only match removal leaves the incumbent and ordinary-ability prior fixed. That is a conservative descriptive comparison, not a causal estimate.

The diagnostic adds zero and ordinary-only forecasts on the same chronological player cohorts as A/B. Forecast comparisons use 4,000 paired whole-match resamples, keeping forecasts and eligibility fixed. Spearman null checks use 20,000 player-label permutations. Seed: 151126. Permutation tests and conditional match-bootstrap intervals answer different questions and need not agree. Selected target/incumbent intervals are exploratory, unadjusted for multiple comparisons, and do not refit baselines or eligibility.

## Main limitations

Model A does not show reliable improvement over zero; its 2026 bowling RMSE is worse. Ordinary ability alone has the lowest 2024-25 development RMSE among the displayed baselines/models. B's point improvements over A are uncertain. The repeatedly inspected 2026 data is a diagnostic, not a fresh confirmation set. External rank transfer has only six comparable batters and three bowlers in 2026.

The newly declared future policy is to freeze a candidate and settings before fresh data, then require a positive 95% paired RMSE-improvement interval against both A and zero before changing the forecasting model. It has not been prospectively tested. A remains the historical contribution score; B is an acquisition sensitivity check. No changes were made to pressure definitions, wicket values, eligibility or the two submitted statistical rankings.

## Fact sources checked

- https://www.iplt20.com/news/article/tata-ipl-2026-player-retentions-announced
- https://www.rajasthanroyals.com/rr-players
- https://www.rajasthanroyals.com/latest-news/ipl-2026-auction-rajasthan-royals-squad-full-players-list
- https://www.cricbuzz.com/cricket-news/140762/bcci-extends-ipl-retention-deadline-to-november-17-cricbuzzcom

2026 club associations are historical labels, not claims about 2027 release/trade status. The 17 November retention deadline and 3 December auction register are attributed to reporting; 3 December is not the auction date.
