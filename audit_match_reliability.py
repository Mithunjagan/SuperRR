"""Rank pressure performance by a lower quartile of match-bootstrap ratings."""

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from rank_pressure import CUTOFF, ROLE_COLUMNS, correlation, f, per_match, pressure, rank, score


SEED = 161126
DRAWS = 8000
QUANTILE = 0.25


def match_rating(matches, player):
    games = matches.sort_index()
    values = games.value.to_numpy()
    balls = games.balls.to_numpy()
    rng = np.random.default_rng(np.random.SeedSequence([SEED, int(player)]))
    draws = rng.integers(len(games), size=(DRAWS, len(games)))
    ratings = 100 * values[draws].sum(axis=1) / (60 + balls[draws].sum(axis=1))
    return float(np.quantile(ratings, QUANTILE))


def build_ranking(matches, names, *, removal=False):
    result = rank(matches).rename(columns={"rating": "model_a"})
    records = []
    for player in result.index:
        games = matches.loc[player]
        value, balls = games.value.sum(), games.balls.sum()
        remaining_rates = 100 * (value - games.value) / (60 + balls - games.balls)
        lowest = remaining_rates.idxmin()
        positive_total = games.value.clip(lower=0).sum()
        row = {
            "player": player,
            "name": names.loc[player],
            "score": match_rating(games, player),
            "worst_leave_one_out": float(remaining_rates.loc[lowest]),
            "positive_matches": int(games.value.gt(0).sum()),
            "largest_positive_share": float(games.value.max() / positive_total) if positive_total else 0.0,
        }
        if removal:
            after = games.drop(lowest)
            if after.balls.sum() >= 60 and len(after) >= 8:
                row["after_removal"] = match_rating(after, player)
        records.append(row)
    table = result.join(pd.DataFrame(records).set_index("player"))
    table["rank_a"] = np.arange(1, len(table) + 1)
    table = table.sort_values(["score", "balls", "player"], ascending=[False, False, True])
    table["rank_reliability"] = np.arange(1, len(table) + 1)
    return table


def metrics(predicted, observed):
    aligned = predicted.reindex(observed.index)
    return {"rmse": round(float(np.sqrt((aligned - observed).pow(2).mean())), 3),
            "spearman": correlation(aligned, observed)}


def forward_diagnostic(role):
    deliveries = score(role, cutoff=CUTOFF)
    eligible = deliveries[deliveries.pressure & deliveries.eligible_event]
    names = deliveries.drop_duplicates("player").set_index("player").name
    train = build_ranking(per_match(eligible[eligible.match_date.lt(CUTOFF)]), names)
    test = per_match(eligible[eligible.match_date.ge(CUTOFF)]).groupby(level="player").agg(
        value=("value", "sum"), balls=("balls", "sum"), matches=("balls", "size"))
    test = test[test.balls.ge(12) & test.matches.ge(3)]
    test = test.loc[test.index.intersection(train.index)]
    observed = 100 * test.value / test.balls
    return {"players": len(test), "model_a": metrics(train.model_a, observed),
            "reliability": metrics(train.score, observed)}


def overlap(a, b):
    return len(set(a.index[:10]) & set(b.index[:10]))


def expanded_pressure(deliveries):
    previous = pressure(deliveries)
    earlier_chase = (
        deliveries.innings.eq(2) & deliveries.left.between(31, 60)
        & deliveries.rrr.between(9.5, 16) & deliveries.lost_before.lt(9)
    )
    return previous | earlier_chase


def deletion_ranking(deliveries, names):
    games = per_match(deliveries)
    rows = []
    for player, summary in games.groupby(level="player"):
        balls = int(summary.balls.sum())
        matches = int(summary.balls.gt(0).sum())
        if matches < 9 or balls - summary.balls.max() < 60:
            continue
        value = float(summary.value.sum())
        leave_one_out = 100 * (value - summary.value) / (60 + balls - summary.balls)
        positive = summary.value.clip(lower=0).sum()
        rows.append({
            "player": player, "name": names.loc[player], "balls": balls, "matches": matches,
            "score": float(leave_one_out.min()), "pooled": 100 * value / (60 + balls),
            "positive_matches": int(summary.value.gt(0).sum()),
            "largest_positive_share": float(summary.value.max() / positive) if positive else 0.0,
            "lift_per100": 100 * summary.lift.sum() / balls,
        })
    table = pd.DataFrame(rows).set_index("player")
    table = table.sort_values(["score", "balls", "player"], ascending=[False, False, True])
    table["rank"] = np.arange(1, len(table) + 1)
    return table


def proposed_ranking(role):
    data = score(role, pressure_selector=expanded_pressure)
    names = data.drop_duplicates("player").set_index("player").name
    eligible = data[data.eligible_event & data.pressure]
    mixed = deletion_ranking(eligible, names)
    chase = deletion_ranking(eligible[eligible.innings.eq(2)], names)
    collapse = eligible[eligible.innings.eq(1)].groupby("player").n.sum()
    ips = eligible[eligible.group.eq("IPL")].groupby("player").n.sum()
    mixed["ipl_balls"] = ips.reindex(mixed.index, fill_value=0)
    mixed["collapse_balls"] = collapse.reindex(mixed.index, fill_value=0)
    mixed["chase_rank"] = chase["rank"].reindex(mixed.index)
    positive_exposure = eligible[eligible.n.gt(0)]
    if role == "Batters":
        positions = positive_exposure.drop_duplicates(["player", "match_id", "innings"])
        mixed["batting_position"] = positions.groupby("player").batting_order.median()
    else:
        phase_balls = positive_exposure.groupby(["player", "phase"], observed=True).n.sum()
        mixed["busiest_phase"] = phase_balls.unstack().fillna(0).idxmax(axis=1)

    freeze = score(role, cutoff=CUTOFF, pressure_selector=expanded_pressure)
    usable = freeze[freeze.pressure & freeze.eligible_event]
    before = usable[usable.match_date.lt(CUTOFF)]
    after = usable[usable.match_date.ge(CUTOFF)]
    train = deletion_ranking(before, names)
    test = per_match(after).groupby(level="player").agg(
        value=("value", "sum"), balls=("balls", "sum"), matches=("balls", "size"))
    test = test[test.balls.ge(12) & test.matches.ge(3)]
    test = test.loc[test.index.intersection(train.index)]
    observed = 100 * test.value / test.balls
    return {
        "eligible": len(mixed),
        "chase_overlap": overlap(mixed, chase),
        "forward": {"players": len(test), "pooled": metrics(train.pooled, observed),
                    "reliability": metrics(train.score, observed)},
        "ranking": json.loads(mixed.reset_index().round(4).to_json(orient="records", force_ascii=False)),
    }


def run():
    reference = json.loads(Path("output/revised_rankings.json").read_text(encoding="utf-8"))
    expanded = expanded_pressure(f)
    report = {"draws": DRAWS, "seed": SEED, "quantile": QUANTILE,
              "pressure_events": int(expanded.sum()),
              "collapse_events": int((expanded & f.innings.eq(1)).sum()),
              "added_chase_events": int((expanded & ~pressure(f)).sum())}
    for role in ROLE_COLUMNS:
        scored = score(role)
        names = scored.drop_duplicates("player").set_index("player").name
        eligible = scored[scored.eligible_event]
        original = eligible.pressure
        broad_chase = eligible.innings.eq(2) & eligible.left.between(1, 60) & eligible.rrr.ge(9.5)
        base = build_ranking(per_match(eligible[original]), names, removal=True)
        chase = build_ranking(per_match(eligible[broad_chase]), names)
        union = build_ranking(per_match(eligible[broad_chase | original]), names)
        by_a = base.sort_values("rank_a")
        assert by_a.name.head(10).tolist() == [r["name"] for r in reference[role]["top"]]
        assert len(base) == reference[role]["eligible"]
        base["rank_after_removal"] = [
            int(1 + (base.loc[base.index != p, "score"] > row.after_removal).sum())
            if pd.notna(row.after_removal) else np.nan for p, row in base.iterrows()]
        base["chase_rank"] = chase.rank_reliability.reindex(base.index)
        base["union_rank"] = union.rank_reliability.reindex(base.index)
        positional = base.sort_values("worst_leave_one_out", ascending=False)
        proposed = proposed_ranking(role)
        proposed_names = {row["player"] for row in proposed["ranking"][:10]}
        proposed["model_a_overlap"] = len(proposed_names.intersection(by_a.index[:10]))
        report[role] = {
            "eligible": len(base),
            "old_window_overlap": overlap(by_a, chase.sort_values("rank_a")),
            "pooled_top10_overlap": overlap(base, by_a),
            "worst_leave_one_out_overlap": overlap(base, positional),
            "chase_overlap": overlap(base, chase),
            "union_overlap": overlap(base, union),
            "top10_still_top10_after_removal": int(base.head(10).rank_after_removal.le(10).sum()),
            "forward": forward_diagnostic(role),
            "proposed": proposed,
            "original": json.loads(base.reset_index().round(4).to_json(orient="records", force_ascii=False)),
            "chase": json.loads(chase.reset_index().round(4).to_json(orient="records", force_ascii=False)),
            "union": json.loads(union.reset_index().round(4).to_json(orient="records", force_ascii=False)),
        }
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    destination = parser.parse_args().output
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(run(), ensure_ascii=False, indent=2), encoding="utf-8")
