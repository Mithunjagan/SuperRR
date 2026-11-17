"""Evaluate ordinary-play priors and match caps without changing submission ranks."""
import json
from pathlib import Path

import numpy as np
import pandas as pd

from rank_pressure import ROLE_COLUMNS, correlation, per_match, rank, score

YEARS = (2024, 2025, 2026)
STRENGTHS = (0, 15, 30, 60, 120, 240)
CAPS = (6, 12, 24)
CLIP_LIMITS = (100, 150, 200)
BASE = ("zero", 60, None)
FAMILIES = {
    "current": [BASE],
    "ordinary_only": [("ordinary_only", None, None)],
    "zero_prior_tuned": [("zero", strength, None) for strength in STRENGTHS],
    "ordinary_prior": [("ordinary", strength, None) for strength in STRENGTHS],
    "robust_match_value": [
        ("clip", strength, limit) for limit in CLIP_LIMITS for strength in STRENGTHS
    ],
    "ordinary_prior_match_cap": [
        ("ordinary", strength, cap) for cap in CAPS for strength in STRENGTHS
    ],
}

def fold(role, year):
    cutoff = f"{year}-01-01"
    end = f"{year + 1}-01-01"
    data = score(role, cutoff=cutoff)
    train = data[data.pressure & data.eligible_event & data.match_date.lt(cutoff)]
    test = data[data.pressure & data.eligible_event & data.match_date.ge(cutoff) & data.match_date.lt(end)]
    train_matches = per_match(train)
    eligible = rank(train_matches)
    test_matches = per_match(test)
    target = test_matches.groupby(level="player").agg(
        value=("value", "sum"), balls=("balls", "sum"), matches=("balls", "size"))
    target = target[target.balls.ge(12) & target.matches.ge(3)]
    target = target.loc[target.index.intersection(eligible.index)]
    target["observed"] = 100 * target.value / target.balls
    ordinary = test.groupby("player").ordinary_rating
    assert ordinary.nunique().max() == 1
    target["ordinary_prior"] = 100 * ordinary.first().reindex(target.index)
    best = train_matches.reset_index().sort_values("value", ascending=False).drop_duplicates("player").set_index("player")
    for cap in CAPS:
        # Keep all events' value, including extras, but cap each player's match contribution.
        weight = cap / train_matches.balls.clip(lower=cap)
        capped = train_matches[["value", "balls"]].mul(weight, axis=0).groupby(level="player").sum()
        target[f"value_{cap}"] = capped.value.reindex(target.index)
        target[f"balls_{cap}"] = capped.balls.reindex(target.index)
        best_weight = cap / best.balls.clip(lower=cap)
        target[f"drop_value_{cap}"] = (best.value * best_weight).reindex(target.index)
        target[f"drop_balls_{cap}"] = (best.balls * best_weight).reindex(target.index)
    for limit in CLIP_LIMITS:
        # Winsorize match means in run equivalents per 100 balls. Preserve charges
        # from matches with only illegal deliveries, whose exposure is zero.
        bound = limit * train_matches.balls / 100
        clipped = train_matches.value.clip(lower=-bound, upper=bound)
        clipped = clipped.where(train_matches.balls.gt(0), train_matches.value)
        target[f"clipped_{limit}"] = clipped.groupby(level="player").sum().reindex(target.index)
        best_bound = limit * best.balls / 100
        target[f"drop_clipped_{limit}"] = best.value.clip(-best_bound, best_bound).where(best.balls.gt(0), best.value).reindex(target.index)
    target["drop_history_value"] = best.value.reindex(target.index)
    target["drop_history_balls"] = best.balls.reindex(target.index)
    target["history_value"] = eligible.value.reindex(target.index)
    target["history_balls"] = eligible.balls.reindex(target.index)
    target["name"] = data.drop_duplicates("player").set_index("player").name.reindex(target.index)
    held_out = test_matches.loc[test_matches.index.get_level_values("player").isin(target.index)]
    return target, held_out

def predict(frame, settings, drop_best=False):
    mode, strength, cap = settings
    if mode == "ordinary_only":
        return frame.ordinary_prior
    if mode == "clip":
        total = frame[f"clipped_{cap}"]
        exposure = frame.history_balls
        if drop_best:
            total = total - frame[f"drop_clipped_{cap}"]
            exposure = exposure - frame.drop_history_balls
    else:
        exposure = frame.history_balls if cap is None else frame[f"balls_{cap}"]
        total = frame.history_value if cap is None else frame[f"value_{cap}"]
        if drop_best:
            exposure = exposure - (frame.drop_history_balls if cap is None else frame[f"drop_balls_{cap}"])
            total = total - (frame.drop_history_value if cap is None else frame[f"drop_value_{cap}"])
    center = frame.ordinary_prior if mode == "ordinary" else 0
    return (100 * total + strength * center) / (exposure + strength)

def rmse(frame, prediction):
    return float(np.sqrt((prediction - frame.observed).pow(2).mean()))

def tune(development, family):
    def loss(settings):
        return float(np.mean([rmse(frame, predict(frame, settings)) ** 2 for frame in development]))
    # The order of each grid provides deterministic tie breaking.
    selected = min(FAMILIES[family], key=loss)
    return selected, float(np.sqrt(loss(selected)))

def paired_interval(frame, test_matches, proposal, rng):
    """Resample evaluation matches jointly, keeping forecasts and eligibility fixed."""
    ids = test_matches.index.get_level_values("match_id").unique()
    def matrix(field):
        return test_matches[field].unstack(fill_value=0).reindex(index=frame.index, columns=ids).to_numpy(float)
    weights = rng.multinomial(len(ids), np.full(len(ids), 1 / len(ids)), size=4000).T
    totals = matrix("value") @ weights
    balls = matrix("balls") @ weights
    observed = np.divide(100 * totals, balls, out=np.full_like(totals, np.nan), where=balls > 0)
    base = predict(frame, BASE).to_numpy()[:, None]
    challenger = proposal.to_numpy()[:, None]
    delta = np.sqrt(np.nanmean((base - observed) ** 2, axis=0))
    delta -= np.sqrt(np.nanmean((challenger - observed) ** 2, axis=0))
    return np.quantile(delta, [.025, .975]).round(3).tolist()

def run():
    results = {"development_years": list(YEARS[:-1]), "evaluation_year": YEARS[-1],
               "adoption_rule": "95% paired match-bootstrap RMSE improvement interval above zero and no loss in holdout Spearman."}
    rng = np.random.default_rng(1126)
    for role in ROLE_COLUMNS:
        frames = {year: fold(role, year) for year in YEARS}
        development = [frames[year][0] for year in YEARS[:-1]]
        assert all(len(frame) >= 3 for frame in development)
        # Select all settings and the challenger before any holdout evaluation.
        choices = {family: tune(development, family) for family in FAMILIES}
        challenger = min(("ordinary_prior", "ordinary_prior_match_cap"), key=lambda family: choices[family][1])
        holdout, test_matches = frames[YEARS[-1]]
        base = predict(holdout, BASE)
        assert np.allclose(base, 100 * holdout.history_value / (holdout.history_balls + 60))
        base_rho = correlation(base, holdout.observed)
        metrics = {}
        for family, (settings, development_rmse) in choices.items():
            prediction = predict(holdout, settings)
            interval = paired_interval(holdout, test_matches, prediction, rng)
            reduced = predict(holdout, settings, drop_best=True)
            top10 = len(set(prediction.nlargest(10).index) & set(reduced.nlargest(10).index))
            metrics[family] = {"settings": settings, "dev_rmse": round(development_rmse, 3),
                               "holdout_rmse": round(rmse(holdout, prediction), 3),
                               "holdout_spearman": correlation(prediction, holdout.observed),
                               "rmse_improvement_95_interval": interval,
                               "top10_after_best_match_removed": top10,
                               "rank_correlation_after_best_match_removed": correlation(prediction, reduced)}
        robust = metrics["robust_match_value"]
        robust["adopt"] = bool(robust["rmse_improvement_95_interval"][0] > 0 and robust["holdout_spearman"] >= base_rho)
        candidate = metrics[challenger]
        adopt = candidate["rmse_improvement_95_interval"][0] > 0 and candidate["holdout_spearman"] >= base_rho
        comparison = holdout[["name", "balls", "matches", "observed", "ordinary_prior"]].copy()
        for family, (settings, _) in choices.items():
            comparison[family] = predict(holdout, settings)
        results[role] = {
            "players_by_year": {year: len(frames[year][0]) for year in YEARS},
            "selected_ordinary_challenger": challenger, "adopt": bool(adopt), "metrics": metrics,
            "holdout_players": json.loads(comparison.reset_index().round(4).to_json(orient="records", force_ascii=False)),
        }
        print(role, results[role]["players_by_year"], challenger, "adopt", adopt, flush=True)
        for family, outcome in metrics.items():
            print(family, outcome, flush=True)
    Path("output/ordinary_prior_validation.json").write_text(
        json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")

if __name__ == "__main__":
    run()



