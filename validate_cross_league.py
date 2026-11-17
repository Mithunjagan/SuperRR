"""Check Model A against Cricsheet club matches and test one public-data prior."""

import argparse
import hashlib
import json
import unicodedata
from collections import Counter, defaultdict
from datetime import date, timedelta
from pathlib import Path
from zipfile import ZipFile

import numpy as np
import pandas as pd

from prepare_deliveries import a, f, read
from rank_pressure import ROLE_COLUMNS, correlation, per_match, pressure, rank, score
from validate_ordinary_prior import YEARS, paired_interval, rmse


LEAGUES = {
    "bbl": ("BBL", "Big Bash League"),
    "psl": ("PSL", "Pakistan Super League"),
    "sat": ("SA20", "SA20"),
    "cpl": ("CPL", "Caribbean Premier League"),
}
HIGHLIGHTED_PLAYERS = {
    "Batters": {"Dewald Brevis", "Heinrich Klaasen"},
    "Bowlers": {"Rashid Khan", "Sunil Narine"},
}
BOWLER_WICKETS = {"bowled", "caught", "caught and bowled", "lbw", "stumped", "hit wicket"}
NON_WICKETS = {"retired hurt", "retired not out"}
WEIGHTS = (0.0, 0.25, 0.5, 0.75, 1.0)


def name_key(value):
    return "".join(ch for ch in unicodedata.normalize("NFKD", value.casefold()) if ch.isalnum())


def team_key(value):
    key = name_key(value)
    return {"unitedstatesofamerica": "usa", "unitedstates": "usa",
            "royalchallengersbangalore": "royalchallengersbengaluru"}.get(key, key)


def match_docs(folder, code):
    with ZipFile(folder / f"{code}_json.zip") as archive:
        for member in sorted(archive.namelist()):
            if member.endswith(".json"):
                yield Path(member).stem, json.loads(archive.read(member))


def team_pair(teams):
    return tuple(sorted(map(team_key, teams)))


def pack_match_index():
    by_teams = defaultdict(list)
    teams = {}
    for match_id, row in a.iterrows():
        sides = {team_key(row.home_team): row.home_team_id, team_key(row.away_team): row.away_team_id}
        by_teams[tuple(sorted(sides))].append((date.fromisoformat(row.match_date), match_id))
        teams[match_id] = sides
    return by_teams, teams


def nearby_matches(by_teams, info):
    match_date = date.fromisoformat(info["dates"][0])
    return [
        (abs((match_date - pack_date).days), pack_id)
        for pack_date, pack_id in by_teams.get(team_pair(info["teams"]), ())
        if abs(match_date - pack_date) <= timedelta(days=1)
    ]


def register_aliases(folder):
    aliases = defaultdict(set)
    for filename, fields in (("people.csv", ("name", "unique_name")), ("names.csv", ("name",))):
        for row in pd.read_csv(folder / filename, dtype=str, keep_default_na=False).to_dict("records"):
            for field in fields:
                aliases[name_key(row[field])].add(row["identifier"])
    return aliases


def aligned_identities(pack_innings, doc, side_ids, candidates):
    """Confirm name variants when both sources record the same full run sequence."""
    registry = doc["info"]["registry"]["people"]
    corroborated = defaultdict(set)
    for number, innings in enumerate((inn for inn in doc["innings"] if not inn.get("super_over")), 1):
        if number not in pack_innings:
            continue
        packed = pack_innings[number]
        if packed.batting_team_id.iat[0] != side_ids[team_key(innings["team"])]:
            continue
        deliveries = [(over["over"] + 1, ball) for over in innings["overs"] for ball in over["deliveries"]]
        runs = [(over, ball["runs"]["batter"], ball["runs"]["total"]) for over, ball in deliveries]
        if runs != list(packed[["overid", "runs", "runs_total"]].itertuples(index=False, name=None)):
            continue
        ids = packed[["striker_id", "bowler_id"]].itertuples(index=False, name=None)
        for (_, ball), (striker, bowler) in zip(deliveries, ids):
            for private_id, field in ((striker, "batter"), (bowler, "bowler")):
                if private_id in candidates:
                    corroborated[private_id].add(registry[ball[field]])
    return corroborated


def verify_identities(folder, evidence, by_teams, pack_teams):
    aliases = register_aliases(folder)
    names = evidence[["player_id", "player"]].drop_duplicates()
    candidates = {row.player_id: aliases[name_key(row.player)] for row in names.itertuples()}
    roster = read("playing_eleven")
    roster = roster[roster.is_played & roster.player_id.isin(candidates)]
    pack_players = roster.groupby(["match_id", "team_id"]).player_id.agg(set).to_dict()
    pack_groups = f.groupby(["match_id", "innings"], sort=False).indices
    corroboration = defaultdict(Counter)
    aligned = defaultdict(Counter)
    paired_scorecards = defaultdict(list)

    for code in ("ipl", "t20s_male"):
        for _, doc in match_docs(folder, code):
            info = doc["info"]
            paired = sorted(nearby_matches(by_teams, info))
            if not paired or (len(paired) > 1 and paired[0][0] == paired[1][0]):
                continue
            distance, pack_id = paired[0]
            paired_scorecards[pack_id].append((distance, doc))

    fixture_audit = Counter()
    for pack_id, public_fixtures in paired_scorecards.items():
        nearest = sorted(public_fixtures, key=lambda item: item[0])
        distance, doc = nearest[0]
        if len(nearest) > 1 and distance == nearest[1][0]:
            fixture_audit["ambiguous_excluded"] += 1
            continue
        fixture_audit["exact_date" if distance == 0 else "one_day_difference"] += 1
        info = doc["info"]
        registry = info["registry"]["people"]
        for side, public_names in info["players"].items():
            pack_team = pack_teams[pack_id][team_key(side)]
            public_ids = {registry[name] for name in public_names}
            for player in pack_players.get((pack_id, pack_team), ()):
                corroboration[player].update(public_ids & candidates[player])
        private_innings = {number: f.iloc[pack_groups[pack_id, number]] for number in (1, 2)
                           if (pack_id, number) in pack_groups}
        for player, people in aligned_identities(private_innings, doc, pack_teams[pack_id], candidates).items():
            aligned[player].update(people)

    audit = []
    for row in names.itertuples():
        confirmed = corroboration[row.player_id]
        plausible = candidates[row.player_id]
        recorded = aligned[row.player_id]
        identifier, scorecards, method = None, 0, None
        if len(confirmed) == 1:
            candidate, support = next(iter(confirmed.items()))
            if (len(plausible) == 1 or support >= 2) and (not recorded or candidate in recorded):
                identifier, scorecards, method = candidate, support, "register alias and team roster"
        if identifier is None and len(recorded) == 1:
            candidate, support = next(iter(recorded.items()))
            if support >= 2 and (not plausible or candidate in plausible):
                identifier, scorecards, method = candidate, support, "matching delivery records"
        audit.append({
            "player_id": row.player_id, "player": row.player,
            "cricsheet_id": identifier, "supporting_scorecards": scorecards, "verification": method,
            "register_candidates": len(plausible),
            "candidate_ids": ",".join(sorted(plausible)),
            "aligned_candidates": ",".join(sorted(recorded)),
        })
    identity = pd.DataFrame(audit)
    linked = identity.dropna(subset=["cricsheet_id"])
    if not linked.player_id.is_unique or not linked.cricsheet_id.is_unique:
        raise ValueError("Player crosswalk is not one-to-one")
    return identity, dict(fixture_audit)


def innings_events(innings, bowling_team, registry, number, target):
    score_before = balls_before = wickets_before = 0
    rows = []
    overs = innings["overs"]
    if not overs or any(over["over"] != idx for idx, over in enumerate(overs)):
        raise ValueError("over sequence")
    for over in overs:
        before_over = balls_before
        over_id = over["over"] + 1
        phase = "Powerplay" if over_id <= 6 else "Middle" if over_id <= 15 else "Death"
        for ball in over["deliveries"]:
            left = 120 - balls_before
            if left <= 0 or wickets_before >= 10 or (number == 2 and score_before >= target):
                raise ValueError("events beyond innings end")
            extras = ball.get("extras", {})
            if extras.get("penalty"):
                raise ValueError("delivery penalty runs")
            wide = extras.get("wides", 0)
            no_ball = extras.get("noballs", 0)
            legal = not (wide or no_ball)
            runs = ball["runs"]["batter"]
            team_runs = ball["runs"]["total"]
            if team_runs != runs + sum(extras.values()):
                raise ValueError("inconsistent run total")
            outs = [wicket for wicket in ball.get("wickets", []) if wicket["kind"] not in NON_WICKETS]
            bat_out = any(
                w["player_out"] == ball["batter"] and w["kind"] != "retired out" for w in outs
            )
            bowl_wicket = any(w["kind"] in BOWLER_WICKETS for w in outs)
            rows.append({
                "innings": number, "phase": phase, "runs_before": score_before,
                "batting_team": innings["team"], "bowling_team": bowling_team,
                "legal_before": balls_before, "lost_before": wickets_before, "left": left,
                "rrr": 6 * (target - score_before) / left,
                "striker_id": registry[ball["batter"]], "striker_name": ball["batter"],
                "bowler_id": registry[ball["bowler"]], "bowler_name": ball["bowler"],
                "runs": runs, "bat_ball": not wide, "bat_out": bat_out, "legal": legal,
                "bowl_event": True, "bowl_runs": runs + wide + no_ball, "bowl_wicket": bowl_wicket,
            })
            score_before += team_runs
            balls_before += legal
            wickets_before += len(outs)
        over_balls = balls_before - before_over
        if over_balls > 6 or (over is not overs[-1] and over_balls != 6):
            raise ValueError("incomplete or miscounted over")
    if wickets_before > 10:
        raise ValueError("too many dismissals")
    return rows, score_before, balls_before, wickets_before


def regular_match(doc):
    info = doc["info"]
    outcome = info["outcome"]
    if info["gender"] != "male" or info["match_type"] != "T20" or info["balls_per_over"] != 6:
        raise ValueError("format")
    if info["overs"] != 20 or outcome.get("method"):
        raise ValueError("revised overs or result method")
    innings = [inn for inn in doc["innings"] if not inn.get("super_over")]
    winner = outcome.get("winner") or outcome.get("eliminator")
    if len(innings) != 2 or not winner:
        raise ValueError("no completed result")
    first, chase = innings
    if any(inn.get("penalty_runs") for inn in innings):
        raise ValueError("innings penalty runs")
    registry = info["registry"]["people"]
    first_rows, first_runs, first_balls, first_wickets = innings_events(first, chase["team"], registry, 1, 0)
    target = first_runs + 1
    chase_target = chase.get("target", {})
    if chase_target.get("overs") != 20 or chase_target.get("runs") != target:
        raise ValueError("revised or missing target")
    chase_rows, chase_runs, chase_balls, chase_wickets = innings_events(chase, first["team"], registry, 2, target)
    if first_balls < 120 and first_wickets < 10:
        raise ValueError("short first innings")
    if chase_runs < target and chase_balls < 120 and chase_wickets < 10:
        raise ValueError("short unfinished chase")
    expected = first["team"] if first_runs > chase_runs else chase["team"]
    margin = outcome.get("by", {})
    if ((first_runs != chase_runs and winner != expected)
            or ("runs" in margin and margin["runs"] != first_runs - chase_runs)
            or ("wickets" in margin and margin["wickets"] != 10 - chase_wickets)):
        raise ValueError("score and result disagree")
    return first_rows + chase_rows


def public_deliveries(folder, by_teams, first_date, last_date):
    rows = []
    audit = {}
    ids, fixtures = set(), set()
    pack_sides = set().union(*map(set, by_teams))
    public_sides = set()
    for code, (league, event) in LEAGUES.items():
        counts = Counter()
        exclusions = Counter()
        archive = folder / f"{code}_json.zip"
        for match_id, doc in match_docs(folder, code):
            counts["archive_matches"] += 1
            info = doc["info"]
            match_date = info["dates"][0]
            if not first_date <= match_date <= last_date:
                continue
            counts["in_window"] += 1
            if info["event"]["name"] != event:
                raise ValueError(f"Unexpected competition in {archive.name}: {info['event']['name']}")
            sides = team_pair(info["teams"])
            public_sides.update(sides)
            fixture = (match_date, sides)
            if nearby_matches(by_teams, info) or match_id in ids or fixture in fixtures:
                exclusions["duplicate fixture"] += 1
                continue
            ids.add(match_id)
            fixtures.add(fixture)
            try:
                balls = regular_match(doc)
            except ValueError as issue:
                exclusions[str(issue)] += 1
                continue
            for ball in balls:
                ball.update(match_id=match_id, match_date=match_date, group=league)
            rows.extend(balls)
            counts["clean_matches"] += 1
        audit[league] = {
            **counts, "exclusions": dict(exclusions),
            "url": f"https://cricsheet.org/downloads/{archive.name}",
            "sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
        }
        assert counts["in_window"] == counts["clean_matches"] + sum(exclusions.values())
    frame = pd.DataFrame(rows)
    frame["phase"] = pd.Categorical(frame.phase, categories=["Powerplay", "Middle", "Death"])
    for league, deliveries in frame.groupby("group"):
        audit[league].update(first_date=deliveries.match_date.min(), last_date=deliveries.match_date.max(),
                             deliveries=len(deliveries), pressure_deliveries=int(pressure(deliveries).sum()))
    return frame, audit, sorted(pack_sides & public_sides)


def match_rows(deliveries):
    keys = ["player", "match_id", "match_date", "group"]
    return deliveries.groupby(keys).agg(
        value=("performance", "sum"), lift=("lift", "sum"), balls=("n", "sum")
    ).reset_index()


def summarize(matches):
    result = matches.groupby("player").agg(
        value=("value", "sum"), lift=("lift", "sum"), balls=("balls", "sum"),
        matches=("match_id", "size"), positive_matches=("value", lambda scores: (scores > 0).sum())
    )
    result["per100"] = 100 * result.value / result.balls.where(result.balls.gt(0))
    result["lift_per100"] = 100 * result.lift / result.balls.where(result.balls.gt(0))
    return result


def enough(summary):
    return summary[summary.balls.ge(12) & summary.matches.ge(3)]


def resampling_matrices(matches, players, rng, draws=2000):
    fixtures = matches[["match_id", "group"]].drop_duplicates().sort_values("match_id")
    weights = np.zeros((len(fixtures), draws))
    for indices in fixtures.reset_index(drop=True).groupby("group").indices.values():
        weights[indices] = rng.multinomial(len(indices), np.repeat(1 / len(indices), len(indices)), size=draws).T
    joined = matches.set_index(["player", "match_id"])
    def totals(field):
        matrix = joined[field].unstack(fill_value=0).reindex(index=players, columns=fixtures.match_id, fill_value=0)
        return matrix.to_numpy(dtype=float) @ weights
    value, balls = totals("value"), totals("balls")
    return np.divide(100 * value, balls, out=np.full_like(value, np.nan), where=balls > 0)


def external_correlation(frame, matches, rng):
    metrics = {"comparable_players": len(frame), "pressure_balls": int(frame.balls.sum()),
               "pressure_matches": int(matches.match_id.nunique()),
               "spearman": correlation(frame.rating, frame.per100),
               "ordinary_spearman": correlation(frame.ordinary_prior, frame.per100)}
    if len(frame) >= 4:
        outcomes = resampling_matrices(matches, frame.index, rng)
        outcomes = outcomes[:, np.isfinite(outcomes).sum(axis=0) >= 3]
        ranks = pd.DataFrame(outcomes, index=frame.index).rank(axis=0)
        forecast = np.broadcast_to(frame.rating.to_numpy()[:, None], outcomes.shape)
        forecast_ranks = pd.DataFrame(np.where(np.isfinite(outcomes), forecast, np.nan), index=frame.index).rank()
        rhos = ranks.corrwith(forecast_ranks).dropna()
        metrics["spearman_match_bootstrap_95"] = rhos.quantile([.025, .975]).round(3).tolist()
    return metrics


def historic_fold(role, year, external_matches, rng):
    cutoff, end = f"{year}-01-01", f"{year + 1}-01-01"
    scores = score(role, cutoff=cutoff)
    eligible = scores[scores.eligible_event & scores.pressure]
    private_train = rank(per_match(eligible[eligible.match_date.lt(cutoff)]))
    history = scores[scores.match_date.lt(cutoff)].groupby("player")[["ordinary_score", "ordinary_n"]].sum()
    private_train["ordinary_prior"] = 100 * history.ordinary_score / (history.ordinary_n + 60)
    frozen = scores[scores.match_date.ge(cutoff)].groupby("player").ordinary_rating
    assert frozen.nunique().max() == 1
    available = private_train.index.intersection(frozen.first().index)
    assert np.allclose(private_train.ordinary_prior.loc[available], 100 * frozen.first().loc[available])
    private_test = eligible[eligible.match_date.ge(cutoff) & eligible.match_date.lt(end)]
    test_matches = per_match(private_test)
    private_target = enough(summarize(match_rows(private_test))).rename(columns={"per100": "observed"})
    public_test = external_matches[external_matches.match_date.ge(cutoff) & external_matches.match_date.lt(end)]
    comparable = private_train[["rating", "ordinary_prior"]].join(enough(summarize(public_test)), how="inner")
    compared_matches = public_test[public_test.player.isin(comparable.index)]
    transfer = external_correlation(comparable, compared_matches, rng)
    transfer.update(pack_eligible_players=len(private_train),
                    public_eligible_players=len(enough(summarize(public_test))))

    public_train = enough(summarize(external_matches[external_matches.match_date.lt(cutoff)]))
    target = private_target.join(
        private_train[["rating", "value", "balls"]].rename(columns={"value": "history_value", "balls": "history_balls"}),
        how="inner",
    ).join(public_train[["per100", "balls"]].add_prefix("public_"), how="left")
    influence = (target.public_balls / (target.public_balls + 60)).fillna(0)
    target["public_delta"] = (target.public_per100.fillna(target.rating) - target.rating) * influence
    return transfer, comparable, target, test_matches.loc[test_matches.index.get_level_values("player").isin(target.index)]


def public_challenger(folds, rng):
    def development_rmse(weight):
        return float(np.sqrt(np.mean([
            rmse(frame, frame.rating + weight * frame.public_delta) ** 2 for _, _, frame, _ in folds[:-1]
        ])))
    selection = min(WEIGHTS, key=development_rmse)
    _, _, holdout, matches = folds[-1]
    base = holdout.rating
    proposed = base + selection * holdout.public_delta
    interval = paired_interval(holdout, matches, proposed, rng)
    base_rho, proposed_rho = correlation(base, holdout.observed), correlation(proposed, holdout.observed)
    return {
        "selected_weight": selection,
        "development_rmse": {str(weight): round(development_rmse(weight), 3) for weight in WEIGHTS},
        "holdout_players": len(holdout), "players_with_public_prior": int(holdout.public_balls.notna().sum()),
        "holdout_rmse_model_a": round(rmse(holdout, base), 3),
        "holdout_rmse_with_public": round(rmse(holdout, proposed), 3),
        "holdout_spearman_model_a": base_rho, "holdout_spearman_with_public": proposed_rho,
        "paired_rmse_improvement_95": interval,
        "adopt": bool(interval[0] > 0 and proposed_rho >= base_rho),
    }


def shortlist_results(evidence, matches, identities, rng):
    player_ids = identities.set_index("player_id").cricsheet_id
    history = summarize(matches)
    recent = summarize(matches[matches.match_date.ge("2026-01-01")])
    qualified = enough(history).index
    qualified_2026 = enough(recent).index
    for pick in evidence[evidence["rank"].le(10)].itertuples():
        row = {"role": pick.role, "rank": pick.rank, "player": pick.player, "model_a": pick.rating,
               "cricsheet_id": player_ids.loc[pick.player_id], "public_qualifies": pick.player_id in qualified,
               "public_2026_qualifies": pick.player_id in qualified_2026}
        sample = matches[matches.player.eq(pick.player_id)]
        row["public_leagues"] = ", ".join(sorted(sample.group.unique()))
        for summary, prefix in ((history, "public"), (recent, "public_2026")):
            if pick.player_id in summary.index:
                stats = summary.loc[pick.player_id]
                for field in ("balls", "matches", "positive_matches", "per100", "lift_per100"):
                    row[f"{prefix}_{field}"] = stats[field]
            else:
                row[f"{prefix}_balls"] = row[f"{prefix}_matches"] = 0
        if pick.player_id in qualified:
            draws = resampling_matrices(sample, [pick.player_id], rng)
            row["public_per100_ci_low"], row["public_per100_ci_high"] = np.nanquantile(draws, [.025, .975])
        yield row


def highlighted_matches(role, picks, eligible_pressure):
    highlights = picks.loc[
        picks["rank"].le(10) & picks.player.isin(HIGHLIGHTED_PLAYERS[role]),
        ["player_id", "player", "rank"],
    ]
    if set(highlights.player) != HIGHLIGHTED_PLAYERS[role]:
        raise ValueError(f"Highlighted players are missing from the {role.lower()} shortlist")
    sample = eligible_pressure[eligible_pressure.player.isin(highlights.player_id)]
    team, opponent = ("batting_team", "bowling_team") if role == "Batters" else ("bowling_team", "batting_team")
    _, _, _, _, _, runs, wickets, _ = ROLE_COLUMNS[role]
    match_keys = ["player", "match_id", "match_date", "group", team, opponent]
    matches = sample.groupby(match_keys).agg(
        pressure_balls=("n", "sum"), pressure_events=("n", "size"),
        role_runs=(runs, "sum"), role_wickets=(wickets, "sum"), raw_value=("v", "sum"),
        adjusted_value=("performance", "sum"), lift=("lift", "sum"),
    ).reset_index().rename(columns={
        "player": "player_id", "match_id": "cricsheet_match_id", "group": "league",
        team: "team", opponent: "opponent",
    })
    # The same player belongs to the same side in both innings.
    assert not matches.duplicated(["player_id", "cricsheet_match_id"]).any()
    matches["expected_value"] = matches.raw_value - matches.adjusted_value
    matches = highlights.merge(matches, on="player_id", validate="1:m").assign(role=role)
    return matches[[
        "role", "rank", "player", "match_date", "league", "cricsheet_match_id", "team", "opponent",
        "pressure_balls", "pressure_events", "role_runs", "role_wickets", "raw_value",
        "expected_value", "adjusted_value", "lift",
    ]].sort_values(["rank", "match_date", "cricsheet_match_id"])


def run(folder, output):
    output.mkdir(parents=True, exist_ok=True)
    evidence = pd.read_csv("output/scouting_player_evidence.csv")
    by_teams, pack_teams = pack_match_index()
    first_date, last_date = f.match_date.min(), f.match_date.max()
    deliveries, audit, common_sides = public_deliveries(folder, by_teams, first_date, last_date)
    identity, fixture_audit = verify_identities(folder, evidence, by_teams, pack_teams)
    checked = identity.dropna(subset=["cricsheet_id"])
    public_presence = set(deliveries.striker_id) | set(deliveries.bowler_id)
    identity["present_in_public_leagues"] = identity.cricsheet_id.isin(public_presence)
    identity.to_csv(output / "player_identity_audit.csv", index=False)
    id_lookup = checked.set_index("cricsheet_id").player_id
    player_names = identity.set_index("player_id").player
    result = {
        "date_window": [first_date, last_date], "archive_audit": audit,
        "shared_team_names": common_sides, "scorecards_for_identity_checks": fixture_audit,
        "identity_source_sha256": {
            file: hashlib.sha256((folder / file).read_bytes()).hexdigest()
            for file in ("ipl_json.zip", "t20s_male_json.zip", "people.csv", "names.csv")
        },
        "ranked_player_identities": len(identity), "verified_identities": len(checked),
        "verified_with_public_appearances": int(identity.present_in_public_leagues.sum()),
        "external_matches": int(deliveries.match_id.nunique()), "external_deliveries": len(deliveries),
        "external_pressure_deliveries": int(pressure(deliveries).sum()),
        "public_minimum": {"prior_ordinary_balls": 120, "pressure_balls": 12, "pressure_matches": 3},
        "pressure_deliveries_by_league_and_year": (
            deliveries[pressure(deliveries)].assign(year=lambda d: d.match_date.str[:4])
            .groupby(["group", "year"]).size().unstack(fill_value=0).to_dict("index")
        ),
        "roles": {},
    }
    rng = np.random.default_rng(20261115)
    shortlist, comparison, breakdown, match_evidence = [], [], [], []
    for role in ROLE_COLUMNS:
        public = score(role, deliveries=deliveries)
        public_pressure = public[public.eligible_event & public.pressure & public.player.isin(id_lookup.index)].copy()
        public_pressure["player"] = public_pressure.player.map(id_lookup)
        external_matches = match_rows(public_pressure)
        picks = evidence[evidence.role.eq(role)]
        shortlist.extend(shortlist_results(picks, external_matches, identity, rng))
        match_evidence.append(highlighted_matches(role, picks, public_pressure))
        for league, matches in external_matches.groupby("group"):
            summaries = summarize(matches).reset_index()
            breakdown.append(summaries.assign(role=role, league=league))
        folds = [historic_fold(role, year, external_matches, rng) for year in YEARS]
        transfer = {}
        for year, (metrics, cohort, _, _) in zip(YEARS, folds):
            transfer[str(year)] = metrics
            comparison.append(cohort.reset_index().assign(role=role, year=year))
        result["roles"][role] = {"transfer": transfer, "public_challenger": public_challenger(folds, rng)}
        print(role, json.dumps(result["roles"][role]), flush=True)
    pd.DataFrame(shortlist).round(6).to_csv(output / "shortlist_external_evidence.csv", index=False)
    pd.concat(match_evidence).round(6).to_csv(output / "highlighted_player_matches.csv", index=False)
    for rows, filename in ((comparison, "walk_forward_players.csv"), (breakdown, "external_results_by_league.csv")):
        frame = pd.concat(rows).rename(columns={"player": "player_id"})
        frame.insert(1, "player", frame.player_id.map(player_names))
        frame.round(6).to_csv(output / filename, index=False)
    (output / "validation.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({key: result[key] for key in (
        "external_matches", "external_deliveries", "external_pressure_deliveries",
        "verified_identities", "ranked_player_identities", "scorecards_for_identity_checks")}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, required=True, help="Directory containing Cricsheet ZIPs and register CSVs")
    parser.add_argument("--output-dir", type=Path, default=Path("output/cross_league"))
    args = parser.parse_args()
    run(args.data_dir, args.output_dir)
