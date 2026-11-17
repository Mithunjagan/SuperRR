"""Recreate Model A evidence and summarize actual Rajasthan Royals deployment."""
import json
from pathlib import Path

import numpy as np
import pandas as pd

from rank_pressure import ROLE_COLUMNS, as_records, bootstrap, f, per_match, rank, score

OUT = Path("output")

def roster_deployment():
    ipl = f[f.group.eq("IPL") & f.year.eq("2026")]
    rr_ids = set(ipl.loc[ipl.home_team.eq("Rajasthan Royals"), "home_team_id"])
    rr_ids |= set(ipl.loc[ipl.away_team.eq("Rajasthan Royals"), "away_team_id"])
    bowling = ipl[ipl.bowling_team_id.isin(rr_ids) & ipl.legal]
    phases = bowling.groupby(["bowler_id", "bowler_name", "phase"], observed=True).size().unstack(fill_value=0)
    phases = phases.reindex(columns=["Powerplay", "Middle", "Death"], fill_value=0)
    phases["Total"] = phases.sum(axis=1)
    batting = ipl[ipl.batting_team_id.isin(rr_ids)].sort_values(["match_id", "innings", "innings_ball_num"])
    slots = batting.drop_duplicates(["striker_id", "match_id", "innings"])
    slots = slots.groupby(["striker_id", "striker_name", "batting_order"]).size().unstack(fill_value=0)
    return {"matches": int(ipl[ipl.home_team_id.isin(rr_ids) | ipl.away_team_id.isin(rr_ids)].match_id.nunique()),
            "bowling": as_records(phases.sort_values("Total", ascending=False)),
            "batting": as_records(slots)}

def main():
    saved = json.loads((OUT / "revised_rankings.json").read_text(encoding="utf-8"))
    all_rows = []
    for role in ROLE_COLUMNS:
        events = score(role)
        events = events[events.pressure & events.eligible_event]
        games = per_match(events)
        ranked = rank(games)
        bootstrap(games, ranked)
        official = {row["player"]: row for row in saved[role]["top"]}
        assert ranked.index[:10].tolist() == list(official)
        by_format = events.groupby(["player", "group"]).agg(balls=("n", "sum"), value=("performance", "sum"))
        for order, (player, row) in enumerate(ranked.iterrows(), 1):
            match = games.loc[player]
            value = match.value
            balls = match.balls
            positive = value.clip(lower=0)
            low, median = np.quantile(value, [.1, .5])
            record = {"role": role, "rank": order, "player_id": int(player),
                      "player": events.loc[events.player.eq(player), "name"].iloc[0], "rating": row.rating,
                      "pressure_balls": int(row.balls), "pressure_matches": len(match),
                      "positive_match_share": float(value.gt(0).mean()),
                      "best_match_share": float(positive.max() / positive.sum()) if positive.sum() else None,
                      "worst_match_value": float(value.min()), "p10_match_value": float(low),
                      "median_match_value": float(median),
                      "bootstrap_top10_share": row.p_top10, "rank_low": int(row.rank_low), "rank_high": int(row.rank_high)}
            for fmt in ("IPL", "T20I"):
                splits = by_format.loc[player] if player in by_format.index.get_level_values("player") else pd.DataFrame()
                split = splits.loc[fmt] if fmt in splits.index else None
                n = int(split.balls) if split is not None else 0
                record[f"{fmt}_pressure_balls"] = n
                record[f"{fmt}_residual"] = float(split.value) if split is not None else 0.0
                record[f"{fmt}_residual_per100"] = 100 * split.value / n if n else None
            assert record["IPL_pressure_balls"] + record["T20I_pressure_balls"] == row.balls
            assert np.isclose(record["IPL_residual"] + record["T20I_residual"], row.value)
            if player in official:
                orig = official[player]
                assert round(row.rating, 4) == orig["rating"] and round(row.p_top10, 4) == orig["p_top10"]
                assert int(row.positive_matches) == orig["positive_matches"]
                record.update({key: orig[key] for key in ("drop_best_rank", "drop_best_balls", "drop_best_rating")})
            all_rows.append(record)
    evidence = pd.DataFrame(all_rows)
    assert len(evidence) == sum(saved[role]["eligible"] for role in ROLE_COLUMNS)
    evidence.to_csv(OUT / "scouting_player_evidence.csv", index=False, float_format="%.6f")
    deployment = roster_deployment()
    (OUT / "rr_2026_deployment.json").write_text(json.dumps(deployment, indent=2, ensure_ascii=False), encoding="utf-8")
    print(evidence[evidence["rank"].le(10)][["role","rank","player","pressure_balls","pressure_matches",
          "positive_match_share","best_match_share","worst_match_value","IPL_pressure_balls","T20I_pressure_balls"]].round(2).to_string(index=False))
    print(json.dumps(deployment, ensure_ascii=False))

if __name__ == "__main__":
    main()

