"""Evaluate role-specific bowling pressure with a fixed Model A target and cohort."""

import json
from pathlib import Path

import numpy as np
import pandas as pd

from rank_pressure import correlation, per_match, rank, score
from validate_ordinary_prior import paired_interval, rmse

VARIANTS = ("A", "D1", "D2")
YEARS = (2024, 2025, 2026)
OUTPUT = Path("output/role_pressure_validation.json")

def strong_platform(data):
    return data.innings.eq(1) & data.legal_before.between(18, 59) & data.lost_before.le(2)

def past_upper_quartile(reference):
    """Use legal deliveries at comparable first-innings states and strictly prior dates."""
    result = pd.Series(np.nan, index=reference.index, dtype=float)
    for _, group in reference.groupby(["group", "phase"], observed=True):
        ordered = group.sort_values("match_date", kind="stable")
        rates = ordered.current_rr.to_numpy()
        prior_legal = ordered.legal.to_numpy()
        for _, positions in ordered.groupby("match_date", sort=True).indices.items():
            start = positions[0]
            previous = rates[:start][prior_legal[:start]]
            if previous.size:
                result.loc[ordered.index[positions]] = np.quantile(previous, 0.75)
    return result

def training_masks(train):
    chase = train.innings.eq(2) & train.pressure
    platform = train.loc[strong_platform(train)].copy()
    platform["current_rr"] = 6 * platform.runs_before / platform.legal_before
    threshold = past_upper_quartile(platform)
    fixed = platform.index[platform.current_rr.ge(9)]
    adaptive = platform.index[threshold.notna() & platform.current_rr.ge(threshold)]
    masks = {"A": train.pressure, "D1": chase | train.index.isin(fixed), "D2": chase | train.index.isin(adaptive)}
    diagnostics = {
        "D2_events_without_prior_reference": int(threshold.isna().sum()),
        "D2_last_thresholds": {
            f"{fmt} {phase}": round(float(series.iloc[-1]), 3)
            for (fmt, phase), group in platform.groupby(["group", "phase"], observed=True)
            if not (series := threshold.loc[group.sort_values("match_date").index].dropna()).empty
        },
    }
    return masks, diagnostics

def exposure_summary(events, history, threshold_matches):
    return {
        "training_balls_all_players": int(events.n.sum()),
        "first_innings_balls_all_players": int(events.loc[events.innings.eq(1), "n"].sum()),
        "chase_balls_all_players": int(events.loc[events.innings.eq(2), "n"].sum()),
        "training_balls_evaluation_players": int(history.balls.sum()),
        "players_under_60_balls": int(history.balls.lt(60).sum()),
        "players_under_8_matches": int(threshold_matches.lt(8).sum()),
        "players_with_zero_balls": int(history.balls.eq(0).sum()),
    }

def compare_year(year):
    cutoff, end = f"{year}-01-01", f"{year + 1}-01-01"
    scored = score("Bowlers", cutoff=cutoff)
    train = scored[scored.match_date.lt(cutoff)]
    masks, diagnostics = training_masks(train)
    train_a = per_match(train[masks["A"] & train.eligible_event])
    control = rank(train_a)
    test = scored[scored.match_date.ge(cutoff) & scored.match_date.lt(end) & scored.eligible_event & scored.pressure]
    matches = per_match(test)
    outcomes = matches.groupby(level="player").agg(
        balls=("balls", "sum"), observed_value=("value", "sum"), matches=("balls", "size"))
    cohort = outcomes[outcomes.balls.ge(12) & outcomes.matches.ge(3)].copy()
    cohort = cohort.loc[cohort.index.intersection(control.index)]
    cohort["observed"] = 100 * cohort.observed_value / cohort.balls
    cohort["name"] = scored.drop_duplicates("player").set_index("player").name.reindex(cohort.index)
    cohort["history_value"] = control.value.reindex(cohort.index)
    cohort["history_balls"] = control.balls.reindex(cohort.index)
    assert len(cohort) >= 3
    output = {"players": len(cohort), "D2_reference": diagnostics, "variants": {}}
    for name in VARIANTS:
        events = train[masks[name] & train.eligible_event]
        history = per_match(events).groupby(level="player").agg(
            value=("value", "sum"), balls=("balls", "sum"), matches=("balls", "size"))
        history = history.reindex(cohort.index, fill_value=0)
        prediction = 100 * history.value / (history.balls + 60)
        cohort[name] = prediction
        cohort[name + "_training_balls"] = history.balls
        cohort[name + "_training_matches"] = history.matches
        output["variants"][name] = {
            "rmse": rmse(cohort, prediction),
            "spearman": correlation(prediction, cohort.observed),
            **exposure_summary(events, history, history.matches),
        }
    assert np.allclose(cohort.A, control.rating.reindex(cohort.index))
    assert len({output["variants"][name]["chase_balls_all_players"] for name in VARIANTS}) == 1
    same_test = matches.loc[matches.index.get_level_values("player").isin(cohort.index)]
    return output, cohort, same_test

def main():
    platform_examples = pd.DataFrame({"innings": [1, 1, 1, 1, 2], "legal_before": [42, 42, 17, 60, 42],
                                      "lost_before": [1, 5, 1, 1, 1]})
    assert strong_platform(platform_examples).tolist() == [True, False, False, False, False]
    previous = json.loads(Path("output/ordinary_prior_validation.json").read_text(encoding="utf-8"))
    development = {year: compare_year(year)[0] for year in YEARS[:-1]}
    def dev_error(variant):
        return float(np.sqrt(np.mean([fold["variants"][variant]["rmse"] ** 2 for fold in development.values()])))
    selected = min(VARIANTS[1:], key=dev_error)
    passed_development = all(
        fold["variants"][selected]["rmse"] < fold["variants"]["A"]["rmse"]
        and fold["variants"][selected]["spearman"] >= fold["variants"]["A"]["spearman"]
        for fold in development.values()
    )
    diagnostic, cohort, test_matches = compare_year(YEARS[-1])
    known = previous["Bowlers"]
    prior_players = pd.DataFrame(known["holdout_players"]).set_index("player")
    assert set(prior_players.index) == set(cohort.index)
    assert np.allclose(prior_players.observed.reindex(cohort.index), cohort.observed, atol=0.0001)
    reference = known["metrics"]["current"]
    assert round(diagnostic["variants"]["A"]["rmse"], 3) == reference["holdout_rmse"]
    assert diagnostic["variants"]["A"]["spearman"] == reference["holdout_spearman"]
    for name in VARIANTS[1:]:
        diagnostic["variants"][name]["rmse_improvement_95_interval"] = paired_interval(
            cohort, test_matches, cohort[name], np.random.default_rng(218))
    candidate = diagnostic["variants"][selected]
    adopt = (passed_development and candidate["rmse_improvement_95_interval"][0] > 0
             and candidate["spearman"] >= diagnostic["variants"]["A"]["spearman"])
    results = {
        "design": "Training pressure selection only. Model A expectations, 120-ball cold start, 60-ball shrinkage, wicket values, batting and chase rules remain fixed.",
        "development_equal_year_rmse": {name: dev_error(name) for name in VARIANTS},
        "selected_by_historical_rmse": selected,
        "passed_both_development_folds": bool(passed_development),
        "adopt": bool(adopt),
        "adoption_rule": "Lower RMSE and no worse Spearman on both historical folds, then positive 95% paired match-bootstrap RMSE improvement and no worse Spearman in 2026.",
        "folds": {**development, YEARS[-1]: diagnostic},
        "diagnostic_players": json.loads(cohort.drop(columns=["history_value", "history_balls"])
                                         .reset_index().round(4).to_json(orient="records", force_ascii=False)),
    }
    OUTPUT.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print("Development-selected:", selected, "Passed both folds:", passed_development, "Adopt:", adopt)
    for year, fold in results["folds"].items():
        print(year, "evaluation players:", fold["players"])
        for name, metrics in fold["variants"].items():
            print(name, {key: round(value, 3) if isinstance(value, float) else value for key, value in metrics.items()})

if __name__ == "__main__":
    main()

