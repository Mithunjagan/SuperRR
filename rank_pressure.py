"""Run from the workspace with Python, pandas and NumPy."""
import json
from pathlib import Path

import numpy as np
import pandas as pd

from prepare_deliveries import a, f

OUT = Path("output")
CUTOFF = "2026-01-01"
RNG = np.random.default_rng(721)
ROLE_COLUMNS = {
    "Batters": ("striker_id", "striker_name", "bowler_id", "bat_ball", "bat_ball", "runs", "bat_out", 1),
    "Bowlers": ("bowler_id", "bowler_name", "striker_id", "bowl_event", "legal", "bowl_runs", "bowl_wicket", -1),
}
COARSE = ["group", "innings", "phase"]
assert len(f) == 184476 and f.match_id.nunique() == 771

def prior(data, keys, values):
    """Sum only earlier date blocks within each group."""
    by_date = data.groupby(keys + ["history_date"], observed=True)[values].sum().sort_index()
    previous = by_date.groupby(level=list(range(len(keys))), observed=True).cumsum() - by_date
    return data[keys + ["history_date"]].join(previous, on=keys + ["history_date"])[values]

def pressure(events, narrow=False):
    remaining, maximum_rate = (24, 17) if narrow else (30, 16)
    chase = events.innings.eq(2) & events.left.between(1, remaining) & events.rrr.between(8, maximum_rate)
    chase &= events.lost_before.lt(9)
    collapse = events.innings.eq(1) & events.lost_before.ge(3) & events.legal_before.lt(60)
    return chase | collapse

def score(role, weights=(8, 6, 4), cutoff=None, legacy=False, *, deliveries=None,
          pressure_selector=pressure):
    player, name, opponent, selected, balls, runs, wicket, sign = ROLE_COLUMNS[role]
    source = f if deliveries is None else deliveries
    d = source[source[selected]].copy().rename(columns={player: "player", name: "name", opponent: "opponent"})
    d["history_date"] = d.match_date if cutoff is None else d.match_date.clip(upper=cutoff)
    d["n"] = d[balls].astype(int)
    wicket_value = d.phase.map(dict(zip(["Powerplay", "Middle", "Death"], weights))).astype(float)
    d["v"] = sign * (d[runs] - wicket_value * d[wicket])
    d["pressure"] = pressure_selector(d)
    d["alternate"] = pressure(d, narrow=True)
    d["segment"] = np.select([d.innings.eq(2) & d.pressure, d.innings.eq(1) & d.pressure],
                             ["chase", "collapse"], default="ordinary")
    d["ordinary_n"] = d.n.where(~d.pressure, 0)
    d["ordinary_v"] = d.v.where(~d.pressure, 0)
    value, count = ("ordinary_v", "ordinary_n") if legacy else ("v", "n")
    phase = prior(d, COARSE, [value, count])
    expectation = (phase[value] + 100 * sign) / (phase[count] + 100)
    if not legacy:
        d["balls_bin"] = (d.left - 1) // np.where(d.left.le(30), 6, 12)
        # Keep late and early bins distinct even where their indices coincide.
        d["balls_bin"] += np.where(d.left.le(30), 0, 10)
        d["wicket_bin"] = np.searchsorted([1, 2, 3, 4, 6, 9], d.lost_before, side="right")
        rate = np.where(d.innings.eq(2), d.rrr, 6 * d.runs_before / d.legal_before.clip(lower=1))
        d["rate_bin"] = np.floor(np.clip(rate, 0, 30) / 2).astype(int)
        coarse_state = COARSE + ["balls_bin", "wicket_bin"]
        for keys, prior_balls in [(coarse_state, 100), (coarse_state + ["rate_bin"], 60)]:
            state = prior(d, keys, ["v", "n"])
            expectation = (state.v + prior_balls * expectation) / (state.n + prior_balls)
        d["state_history_balls"] = state.n
    d["residual"] = d.v - expectation * d.n
    d["ordinary_residual"] = d.residual.where(~d.pressure, 0)
    opp_history = prior(d, ["opponent"] + COARSE, ["ordinary_residual", "ordinary_n"])
    d["performance"] = d.residual - opp_history.ordinary_residual / (opp_history.ordinary_n + 60) * d.n
    d["ordinary_score"] = d.performance.where(~d.pressure, 0)
    player_history = prior(d, ["player"], ["ordinary_score", "ordinary_n"])
    d["ordinary_rating"] = player_history.ordinary_score / (player_history.ordinary_n + 60)
    d["lift"] = d.performance - d.ordinary_rating * d.n
    d["eligible_event"] = player_history.ordinary_n.ge(120)
    return d

def per_match(d):
    return d.groupby(["player", "match_id"]).agg(
        value=("performance", "sum"), lift=("lift", "sum"), balls=("n", "sum"))

def rank(matches, legacy=False):
    summary = matches.groupby(level="player").agg(
        value=("value", "sum"), lift=("lift", "sum"), balls=("balls", "sum"),
        matches=("balls", "size"))
    summary = summary[summary.balls.ge(60) & summary.matches.ge(8)].copy()
    numerator = 0.7 * summary.value + 0.3 * summary.lift if legacy else summary.value
    summary["rating"] = 100 * numerator / (summary.balls + 60)
    summary["per100"] = 100 * summary.value / summary.balls
    summary["lift_per100"] = 100 * summary.lift / summary.balls
    return summary.sort_values(["rating", "balls", "player"], ascending=[False, False, True])

def as_records(frame):
    return json.loads(frame.reset_index().round(4).to_json(orient="records", force_ascii=False))

def bootstrap(matches, rankings):
    original = matches.loc[matches.index.get_level_values("player").isin(rankings.index)]
    ids = original.index.get_level_values("match_id").unique()
    def matrix(column):
        return original[column].unstack(fill_value=0).reindex(
            index=rankings.index, columns=ids, fill_value=0).to_numpy(dtype=float)
    draws = RNG.multinomial(len(ids), np.full(len(ids), 1 / len(ids)), size=1000).T
    values = 100 * (matrix("value") @ draws) / (matrix("balls") @ draws + 60)
    order = np.argsort(np.argsort(-values, axis=0), axis=0) + 1
    rankings["p_top10"] = (order <= 10).mean(axis=1)
    rankings["rank_low"] = np.quantile(order, .025, axis=1, method="nearest").astype(int)
    rankings["rank_high"] = np.quantile(order, .975, axis=1, method="nearest").astype(int)
    rankings["positive_matches"] = original.value.gt(0).groupby(level="player").sum()

def correlation(a, b):
    value = a.rank().corr(b.rank())
    return None if pd.isna(value) else round(float(value), 3)

def holdout(role):
    sample = score(role, cutoff=CUTOFF)
    old = score(role, cutoff=CUTOFF, legacy=True)
    for frame in (sample, old):
        assert frame.loc[frame.match_date.ge(CUTOFF)].groupby("player").ordinary_rating.nunique().max() == 1
    def get_train(frame):
        return frame[frame.eligible_event & frame.pressure & frame.match_date.lt(CUTOFF)]
    main = rank(per_match(get_train(sample)))
    old_order = rank(per_match(get_train(old)), legacy=True)
    test = sample[sample.eligible_event & sample.pressure & sample.match_date.ge(CUTOFF)]
    later = per_match(test)
    outcomes = later.groupby(level="player").agg(value=("value", "sum"), balls=("balls", "sum"),
                                                matches=("balls", "size"))
    outcomes = outcomes[outcomes.balls.ge(12) & outcomes.matches.ge(3)]
    same = main.join(outcomes.add_prefix("later_"), how="inner")
    same = same.join(old_order.rating.rename("old_rating"), how="inner")
    ordinary = test.groupby("player").ordinary_rating.first()
    same["ordinary"] = ordinary.reindex(same.index)
    same["outcome"] = 100 * same.later_value / same.later_balls
    return {"n": len(same), "train": len(main), "new": correlation(same.rating, same.outcome),
            "original": correlation(same.old_rating, same.outcome),
            "ordinary": correlation(same.ordinary, same.outcome)}

def overlap(reference, candidate):
    return len(set(reference.index[:10]) & set(candidate.index[:10]))

def main():
    with (OUT / "original_rankings.json").open(encoding="utf-8") as fh:
        original = json.load(fh)
    result = {"matches": int(f.match_id.nunique()), "events": len(f),
              "pressure_events": int(pressure(f).sum()),
              "format_matches": f.groupby("group").match_id.nunique().to_dict()}
    for role in ROLE_COLUMNS:
        d = score(role)
        included = d[d.eligible_event]
        evaluated = included[included.pressure]
        matches = per_match(evaluated)
        ranking = rank(matches)
        names = d.drop_duplicates("player").set_index("player").name
        ranking["name"] = names.reindex(ranking.index)
        ranking["rank"] = np.arange(1, len(ranking) + 1)
        bootstrap(matches, ranking)
        top = ranking.head(10).copy()
        for player in top.index:
            games = matches.loc[player]
            best = games.value.idxmax()
            remaining = games.drop(best)
            top.loc[player, "best_positive_share"] = games.value.max() / games.value.clip(lower=0).sum()
            top.loc[player, "drop_best_balls"] = int(remaining.balls.sum())
            top.loc[player, "drop_best_rating"] = 100 * remaining.value.sum() / (remaining.balls.sum() + 60)
            if remaining.balls.sum() >= 60 and len(remaining) >= 8:
                others = ranking.drop(player).rating
                top.loc[player, "drop_best_rank"] = int(1 + (others > top.loc[player, "drop_best_rating"]).sum())
        windows = rank(per_match(included[included.alternate]))
        splits = {}
        for fmt in ["IPL", "T20I"]:
            subset = rank(per_match(evaluated[evaluated.group.eq(fmt)]))
            subset["name"] = names.reindex(subset.index)
            subset["rank"] = np.arange(1, len(subset) + 1)
            splits[fmt] = {"eligible": len(subset), "overlap": overlap(ranking, subset),
                           "top": as_records(subset.head(10)[["name", "rank", "rating", "balls", "matches"]])}
        sensitivity = {}
        for label, weights in [("flat", (6, 6, 6)), ("half", (4, 3, 2)), ("higher", (12, 9, 6))]:
            alternate = score(role, weights)
            alternative_order = rank(per_match(alternate[alternate.eligible_event & alternate.pressure]))
            sensitivity[label] = {"overlap": overlap(ranking, alternative_order),
                                  "leader": names.loc[alternative_order.index[0]]}
        orig = {row["player_id"]: order for order, row in enumerate(original[role]["top"][:10], 1)}
        top["original_rank"] = top.index.map(orig)
        cold_lost = int(d.loc[d.pressure & ~d.eligible_event, "n"].sum())
        cold_total = int(d.loc[d.pressure, "n"].sum())
        result[role] = {"top": as_records(top), "eligible": len(ranking),
                        "original_overlap": len(set(top.index) & set(orig)),
                        "window_overlap": overlap(ranking, windows), "split": splits,
                        "sensitivity": sensitivity, "holdout": holdout(role),
                        "cold_lost": cold_lost, "cold_total": cold_total,
                        "fine_state_median": float(evaluated.state_history_balls.median()),
                        "fine_state_empty_pct": float(evaluated.state_history_balls.eq(0).mean())}
        print(role, result[role]["holdout"], sensitivity, flush=True)
        print(top[["name", "rating", "p_top10", "original_rank"]].round(2).to_string(), flush=True)
    (OUT / "revised_rankings.json").write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

if __name__ == "__main__":
    main()

