# SupeRR Selector Round 1 | External pressure validation

Model A remains the basis for both top-10 lists. The public data corroborates individual picks and shows limited transfer of the full player ordering.

## Evidence for the methodology report

We applied Model A’s pressure definition to 610 quality-checked men’s T20 matches from the Big Bash League, Pakistan Super League, SA20 and Caribbean Premier League. The four leagues contributed 11,422 pressure deliveries and had zero fixture overlaps with the supplied pack. Ten of the 20 shortlisted players met the external sample minimum. In 2026, rankings estimated from pre-2026 IPL and T20I data had Spearman correlations of −0.43 for six batters and −0.50 for three bowlers against later public-league pressure outcomes. The overlap is too small to draw a broad conclusion about the player ordering. Public evidence was used to corroborate individual cases, and Model A determined both submitted lists.

| Shortlisted player | Public leagues | Pressure balls / matches | Adjusted performance per 100 | Lift vs own ordinary play per 100 |
|---|---|---:|---:|---:|
| Dewald Brevis | SA20 | 74 / 9 | +43.17 | +29.53 |
| Heinrich Klaasen | SA20 | 96 / 12 | +30.29 | −6.32 |
| Rashid Khan | BBL, CPL, PSL, SA20 | 83 / 13 | −8.27 | −25.38 |
| Sunil Narine | CPL, SA20 | 64 / 11 | +68.68 | +34.19 |

Brevis was above his SA20 match-state benchmark in eight of nine pressure matches. His match-bootstrap interval for adjusted performance was +14.39 to +82.84 per 100. Narine was positive in nine of 11 matches, with an interval of +30.05 to +102.81. Most of Narine’s exposure was in the CPL (58 of 64 balls). Klaasen cleared the SA20 benchmark on average and fell below his own ordinary-performance baseline. Rashid’s pooled estimate was negative with a wide interval crossing zero. His SA20 sample accounted for 54 of his 83 pressure balls.

## Match-level contributions

The match evidence contains 45 player-match rows for the four highlighted players. The adjusted value is the sum of run equivalents above or below the context and opponent expectation in that match. Pressure balls are batting exposure for batters and legal deliveries for bowlers. The event count includes eligible extras that carry value. Role runs are runs off the bat or runs charged to the bowler. Role wickets are striker dismissals or credited bowling wickets, according to Model A.

| Player | Lowest adjusted match | Pressure balls | Adjusted match value | Pooled rate per 100 if omitted |
|---|---|---:|---:|---:|
| Dewald Brevis | Durban’s Super Giants, 23 January 2024 (SA20) | 2 | -0.34 | +44.85 |
| Heinrich Klaasen | Joburg Super Kings, 30 December 2025 (SA20) | 7 | -5.55 | +38.91 |
| Rashid Khan | Sunrisers Eastern Cape, 18 January 2023 (SA20) | 6 | -19.64 | +16.59 |
| Sunil Narine | Guyana Amazon Warriors, 5 September 2023 (CPL) | 3 | -5.51 | +81.09 |

Rashid’s eight positive matches added +37.28 run equivalents. His five negative matches contributed -44.15, for a total of -6.87. In the lowest match he conceded 28 charged runs in six pressure balls and took zero wickets. His raw bowling value of -28.00 and the context expectation of -8.36 yield -19.64. Omitting that match changes his public rate from -8.27 to +16.59 per 100. This sensitivity test uses the same match scores and removes both the match value and its ball count.

Brevis (+29.58) and Narine (+58.50) still have positive public rates per 100 when their individual best match is omitted. Tim David (-29.04) and Naveen ul Haq (-19.74) provide counterexamples to general rank transfer.

## Match coverage

| Cricsheet competition | In-window matches | Retained | Deliveries | Pressure deliveries |
|---|---:|---:|---:|---:|
| BBL | 192 | 175 | 41,526 | 3,287 |
| PSL | 177 | 169 | 40,419 | 2,885 |
| SA20 | 130 | 117 | 27,395 | 2,335 |
| CPL | 167 | 149 | 35,585 | 2,915 |
| Total | 666 | 610 | 144,925 | 11,422 |

The window runs from 22 January 2022 through 1 November 2026, inclusive, matching the usable supplied data. The most recent retained public fixture was on 20 September 2026. We checked fixtures by Cricsheet match ID within public archives and by normalized team pair and date across the sources, allowing a one-day date difference. A team-name audit found zero shared normalized team names. We filtered revised or incomplete matches and rechecked chase targets, over budgets and score margins. We used regulation deliveries from qualifying matches.

We linked 85 of the 86 distinct ranked players, including all 20 shortlisted players, using the Cricsheet Register and same-team rosters or matching delivery records from shared IPL and T20I scorecards. The affected records for the unresolved identity were excluded. Shared scorecards supplied identity evidence only.

## Model specification

- Pressure in the first innings means at least three wickets lost before 60 legal balls. Chase pressure means 1–30 legal balls left, 8–16 required runs per over and fewer than nine wickets lost.
- We reused the 8, 6 and 4 run-equivalent wicket costs in the powerplay, middle and death overs. Positive batting value means runs added, and positive bowling value means runs saved. Context-adjusted values use the league’s own earlier match states and the opponent’s earlier ordinary performance. Dates equal to the match date contribute zero baseline information.
- Public results require at least 120 prior ordinary balls in the role, as in Model A. A public player sample qualifies at 12 pressure balls across three matches. Public performance is the unshrunk adjusted value per 100 role balls. Lift subtracts the player’s own prior ordinary-performance baseline, estimated from public matches.
- The shortlist table pools eligible exposures through the end of the window. It describes individual public performance. The model transfer comparison below uses ratings computed as of 1 January of each evaluation year and only uses subsequent outcomes within that year. The sample requires Model A’s original training eligibility.

| Evaluation year | Batters (players / pressure balls / Spearman) | Bowlers (players / pressure balls / Spearman) |
|---|---:|---:|
| 2024 | 5 / 168 / 0.00 | 2 / 41 / −1.00 |
| 2025 | 7 / 225 / −0.04 | 3 / 93 / −1.00 |
| 2026 | 6 / 153 / −0.43 | 3 / 86 / −0.50 |

Match-bootstrap intervals use 2,000 draws within public leagues and reflect variation within the observed player group. The 2026 interval for batters was [−1.00, +0.09]. When three or fewer bowlers qualified, the ordering of a handful of players drove the correlation. Ten shortlist players lacked a qualifying public sample. These limitations matter for interpreting the transfer results.

## Public-data forecasting test

We also tested a weighted public prior for predicting later IPL and T20I pressure performance. The adjusted public rate used matches before 1 January of each evaluation year. The blend gave public evidence a weight of `lambda * n / (n + 60)`, where `n` is the public pressure-ball count. Players who lacked a qualifying public sample kept their Model A forecast. We selected `lambda` on 2024–25 and evaluated the chosen value on 2026.

| Role | Selected lambda | Evaluation players with public prior / total | Model A RMSE | With public prior RMSE | Model A Spearman | With public prior Spearman |
|---|---:|---:|---:|---:|---:|---:|
| Batters | 0.00 | 5 / 14 | 51.048 | 51.048 | 0.398 | 0.398 |
| Bowlers | 0.75 | 6 / 16 | 59.034 | 58.236 | 0.218 | 0.176 |

The bowler RMSE improvement was +0.798 run equivalents per 100 balls, with a 95% paired match-bootstrap interval of [−1.876, +3.370]. Model A’s adoption rule requires the interval to clear zero and Spearman to hold or improve. Both roles retained Model A. The original ranked IDs and ratings were reproduced for all 94 player-role rows.

## Reproduce

Use the existing Round 1 reproduction folder and its supplied pack. Unzip this addendum’s Python files into that folder. Use Python 3.11 or later with pandas, NumPy and ReportLab.

Download the following files into a directory of your choice. The IPL and T20I archives supply the identity audit. The four club competition archives supply the performance evidence.

- [BBL JSON](https://cricsheet.org/downloads/bbl_json.zip) · [PSL JSON](https://cricsheet.org/downloads/psl_json.zip) · [SA20 JSON](https://cricsheet.org/downloads/sat_json.zip) · [CPL JSON](https://cricsheet.org/downloads/cpl_json.zip)
- [IPL JSON](https://cricsheet.org/downloads/ipl_json.zip) · [Men’s T20I JSON](https://cricsheet.org/downloads/t20s_male_json.zip) · [People register](https://cricsheet.org/register/people.csv) · [Name variants](https://cricsheet.org/register/names.csv)

Run from the reproduction folder.

~~~sh
python validate_cross_league.py --data-dir path/to/cricsheet --output-dir output/cross_league
python render_scouting_dossier.py --external-validation output/cross_league --output output/pdf/SupeRR_Round_1_Scouting_Dossier.pdf
~~~

The output includes shortlist exposures, per-league residuals, match-by-match results, each walk-forward comparison, and the identity audit. Archive SHA-256 hashes and filtration counts are in `validation.json`. The addendum contains derived evidence and analysis code. The supplied ball-by-ball data stays in the original reproduction folder.

Source data by Cricsheet, retrieved 15 November 2026. The match records and register are available under the Open Data Commons Attribution License 1.0. [Match downloads](https://cricsheet.org/downloads/) · [Register](https://cricsheet.org/register/) · [License](https://cricsheet.org/licensing/)
