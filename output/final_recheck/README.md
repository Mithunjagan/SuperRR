# SupeRR final recheck - 17 November 2026

This archive accompanies the revised eleven-page Round 1 report. It contains the exact final dropdown order and reproducible evidence. It does not contain or redistribute the confidential Data Pack.

## The decision

Rank both roles by the unrounded worst leave-one-match-out score, highest first. Exact ties use more qualifying balls, then lower supplied player ID. Bootstrap, chase-only results and IPL exposure are sensitivity evidence. Hosein ranks first and Bumrah ranks second on this common scale.

Hosein still leads the raw deletion score 22.096441 versus 21.656704. Bumrah leads Q25, 19.414367 versus 18.775451, and the chase-only order, with 113 IPL balls versus 24. Joint-fixture resampling favours Bumrah in 53.13% of 20,000 draws; that is not decisive statistical separation. Hosein has the larger positive-match share and the lower largest-positive-match concentration.

## Reproduce

Put the original `Data Pack` folder beside the scripts. The CSV hashes are in `output/final_recheck/final_rankings.json`. Python 3.12.14, pandas and NumPy versions are recorded there. Install pandas, numpy and reportlab; pypdf is needed for verification.

Run from the archive root:

```text
python audit_final_recheck.py
python finalize_recheck.py
python render_final_dossier.py
```

`prepare_deliveries.py` screens matches and builds pre-delivery context. `rank_pressure.py` supplies earlier-date expected contributions and ordinary-player history. `audit_match_reliability.py` supplies the expanded pressure definition and deletion eligibility/rating functions. Its older standalone renderer is not used by this recheck. `reference_before_recheck.json` records the prior result so the new audit can assert exact recovery before doing additional checks.

The presentation update leaves both ranking lists unchanged. The renderer reads frozen results.json, calibration.csv and bowl_rankings.csv from output/leverage_analysis to reproduce the two evidence figures and the leverage comparison. All three inputs are included in this archive.

The authoritative final artifact is `output/pdf/SupeRR_Round_1_Scouting_Dossier.pdf`. The authoritative final table is `output/final_recheck/Unstop_Submission_Order.csv`. Both are generated from `final_rankings.json`. The live Unstop dropdown selections were not inspected or submitted.

The 2027 availability input is output/final_recheck/ipl_2027_availability.csv. Record Retained or Released from official 2027 announcements and use the reported variants for sourced media coverage. The source column records the underlying link for either type. Set pool_status to Confirmed only for an official auction-pool entry. The renderer filters the full eligible order, so verified names below rank 10 can appear on page 8. The Round 1 dropdown order is calculated independently.

## Main evidence

- Same-window chase-only top-ten overlap: 5/10 batters; 7/10 bowlers. Re-estimating ordinary history under chase-only gives the same overlaps.
- Revised-list Q25 bootstrap top-ten overlap: 9/10 in each role. Ishan Kishan replaces Buttler; Roston Chase replaces Santner. This is a sensitivity check, not the adopted full ranking.
- Equal-eight-match Q25 bootstrap overlap with final membership: 9/10 batters, 7/10 bowlers. The fixed budget discards evidence and is not a replacement model.
- Hendricks: 82 qualifying chase balls in six innings. Chapman: 48 in three. Their mixed-window eligibility depends on first-innings collapse states. Gill and Buttler have eight chase innings, so they fail the requirement to retain eight after deletion.
- Hosein: 150 mixed-window pressure balls before the ordinary-history filter, 42 removed, 108 used. Eligible sample economy is 6.00 from 108 charged runs. These are not the quoted 126 balls / 6.9 economy.
- Forecast RMSE: deletion 50.434 versus zero 44.691 for 26 batters; deletion 47.021 versus zero 43.690 for 30 bowlers. Spearman -0.263 / +0.042. Predictive power remains unproven.

The RR role notes on pages 9-10 use the screened regulation data in prepare_deliveries.f. Batting phases use bat_ball and runs off the bat. Bowling phase totals count legal balls and credited wickets on those balls. Opening innings use batting_order 1 or 2 and count distinct match and innings pairs. Pressure-only counts use the corresponding role audit. Archer's RR figures come from output/rr_2026_deployment.json.

## Sampling details

Player-level bootstrap: sample the player's complete observed match records with replacement, using their original record count; 20,000 draws. Preserve zero-exposure extras-only bowling matches as value records without counting them toward the eight-positive-exposure-match gate. Use NumPy SeedSequence [161126, supplied player ID, sampled match count]. Q25 is the 25th percentile of 100 x sampled adjusted value / (sampled exposure + 60). The equal-eight diagnostic samples eight records instead. Scores, expected values, ordinary history and eligibility stay fixed.

The separate leading-bowler check resamples the 44-match fixture union with a multinomial weight vector shared by the two players; the two have no shared qualifying fixture. Seed 161126, 20,000 draws. It preserves complete fixture contributions and allows player-specific observed exposure to vary across resamples. The middle 95% of the difference spans -32.773725 to +37.747121.

All resampling describes conditional historical uncertainty. It does not refit the full model, adjust for model selection or establish future superiority. The 2026 period has been repeatedly inspected. Model choices are retrospective.

## Independent files

`batters_match_evidence.csv` and `bowlers_match_evidence.csv` retain per-player, per-match adjusted value, lift and balls. The split CSVs retain innings/format totals. Full eligibility cohorts and all diagnostics are in `audit.json` and the role audit CSVs. The retained external-league audit uses the original pressure definition and is not rerun or promoted to validation of the new ranking.

No athlete is assumed available at auction. Squad comparisons are descriptive and kept outside statistical selection. No top-16 selection probability is estimated.
