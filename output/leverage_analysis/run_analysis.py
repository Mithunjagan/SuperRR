"""Rolling T20 win probability, counterfactual leverage and player WPA.

Run from the project root: python output/leverage_analysis/run_analysis.py
Requires NumPy and pandas. The original six supplied CSVs stay in Data Pack.
"""
import hashlib
import json
from collections import defaultdict
from pathlib import Path
import sys

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from prepare_deliveries import a as MATCHES, f as EVENTS
from audit_match_reliability import expanded_pressure
from rank_pressure import prior

OUT = Path(__file__).resolve().parent
YEARS = [2023, 2024, 2025, 2026]
SEED = 20261116
DRAWS = 6000


def sigmoid(x):
    return 1 / (1 + np.exp(-np.clip(x, -35, 35)))


def logit(x):
    p = np.clip(x, 0.0001, 0.9999)
    return np.log(p / (1 - p))


def fit_logistic(x, y, penalty=6.0, nonnegative=(), nonpositive=()):
    weights = np.zeros(x.shape[1])
    ridge = np.full(x.shape[1], penalty)
    ridge[0] = 0.001
    lower, upper = np.full(x.shape[1], -np.inf), np.full(x.shape[1], np.inf)
    lower[list(nonnegative)] = 0
    upper[list(nonpositive)] = 0

    def loss(beta):
        score = x @ beta
        return np.sum(np.logaddexp(0, score) - y * score) + 0.5 * np.sum(ridge * beta**2)

    for _ in range(40):
        p = sigmoid(x @ weights)
        curvature = np.maximum(p * (1 - p), 1e-7)
        gradient = x.T @ (p - y) + ridge * weights
        fixed = ((weights <= lower+1e-10) & (gradient > 0)) | ((weights >= upper-1e-10) & (gradient < 0))
        free = ~fixed
        xs = x[:,free]
        hessian = xs.T @ (curvature[:,None] * xs) + np.diag(ridge[free])
        descent = np.zeros_like(weights)
        descent[free] = np.linalg.solve(hessian, gradient[free])
        start = loss(weights)
        moved = False
        for direction in (descent, gradient / len(y)):
            for alpha in (1, .5, .25, .125, .0625, .03125, .015625, .0078125):
                update = np.clip(weights - alpha * direction, lower, upper)
                if loss(update) < start - 1e-8:
                    moved = True
                    break
            if moved:
                break
        if not moved or np.max(np.abs(weights-update)) < 1e-6:
            break
        weights = update
    return weights



def fit_platt(p, y):
    return fit_logistic(np.column_stack((np.ones(len(p)), logit(p))), y, 0.3, nonnegative=(1,))


def context_table():
    fmt_totals, venue_totals, elo = {}, {}, {}
    rows = []
    matches = MATCHES[MATCHES.is_clean].reset_index().sort_values(["match_date", "match_id"])
    for _, daily in matches.groupby("match_date", sort=False):
        changes = defaultdict(float)
        for m in daily.itertuples(index=False):
            fmt, v = m.group, (m.group, m.venue_id)
            total, n = fmt_totals.get(fmt, (0, 0))
            par = (total + 20 * 165) / (n + 20)
            total, n = venue_totals.get(v, (0, 0))
            venue_par = (total + 15 * par) / (n + 15)
            e1, e2 = (elo.get((fmt, team), 0) for team in (m.team1, m.team2))
            y1 = 0.5 if m.score1 == m.score2 else float(m.score1 > m.score2)
            upset = y1 - float(sigmoid((e1 - e2) / 1.75))
            changes[(fmt, m.team1)] += 0.10 * upset
            changes[(fmt, m.team2)] -= 0.10 * upset
            rows.append((m.match_id, par, venue_par, e1 - e2, y1, int(m.score1) + 1))
        for m in daily.itertuples(index=False):
            for totals, key in ((fmt_totals, m.group), (venue_totals, (m.group, m.venue_id))):
                total, n = totals.get(key, (0, 0))
                totals[key] = (total + m.score1, n + 1)
        for key, change in changes.items():
            elo[key] = elo.get(key, 0) + change
    return pd.DataFrame(rows, columns=["match_id", "par", "venue_par", "elo1", "y1", "target"])


def quality(d, player, eligible, raw):
    work = d[["group", "innings", "phase", "match_date", player]].copy()
    work["history_date"] = work.match_date
    work["balls"] = eligible.astype(int)
    work["raw"] = raw * work.balls
    context = prior(work, ["group", "innings", "phase"], ["raw", "balls"])
    expected = (context.raw + 60 * (0.85 if player == "striker_id" else -0.85)) / (context.balls + 60)
    work["residual"] = (raw - expected) * eligible
    same_format = prior(work, [player, "group"], ["residual", "balls"])
    pooled = prior(work, [player], ["residual", "balls"])
    pooled_quality = pooled.residual.fillna(0) / (pooled.balls.fillna(0) + 150)
    return (same_format.residual.fillna(0) + 100 * pooled_quality) / (same_format.balls.fillna(0) + 100)


def build_data():
    d = EVENTS.reset_index(drop=True).merge(context_table(), on="match_id", validate="many_to_one")
    d["ipl"] = d.group.eq("IPL").astype(int)
    d["bat_quality"] = quality(d, "striker_id", d.bat_ball, d.runs - 6 * d.bat_out)
    d["bowl_quality"] = quality(d, "bowler_id", d.legal, 6 * d.bowl_wicket - d.bowl_runs)
    d["y"] = np.where(d.innings.eq(1), d.y1, 1 - d.y1)
    assert len(d) == 184476 and d.match_id.nunique() == 771
    assert not d[["runs_total", "left", "lost_before", "y", "bat_quality", "bowl_quality"]].isna().any().any()
    assert not d.duplicated(["match_id", "innings", "innings_ball_num"]).any()
    return d


def features(innings, b, w, s, target, par, venue, elo1, ipl, rich):
    n = len(b)
    ball = np.clip(b, 1, 120)
    available = ball / 120
    wk = np.clip(w, 0, 10) / 10
    if innings == 1:
        baseline = venue if rich else par
        pace = 120 * (s + baseline / 4) / (150 - ball)
        projection = s + available * (0.65 * baseline + 0.35 * pace) * (1 - wk) ** 0.35
        margin = (projection - baseline) / 35
        x = [np.ones(n), np.minimum(margin+0.6, 0), np.clip(margin+0.6,0,1.2),
             np.maximum(margin-0.6,0), wk, wk*available, available, ipl]
    else:
        need = target - s
        baseline = venue if rich else par
        capacity = baseline * available * (1 - wk) ** 0.32
        margin = (capacity - need) / (3.3 * np.sqrt(ball + 1))
        x = [np.ones(n), np.minimum(margin+0.8,0), np.clip(margin+0.8,0,1.6),
             np.maximum(margin-0.8,0), wk, wk*available, available, ipl,
             np.sqrt(available), np.log1p(ball)/5]
    if rich:
        x.extend([elo1 if innings == 1 else -elo1, (venue - par) / 30])
    return np.column_stack(x)


STATIC = ["target", "par", "venue_par", "elo1", "ipl"]


def get_features(d, innings, rich):
    return features(innings, *d[["left", "lost_before", "runs_before", *STATIC]].to_numpy().T, rich)


def predict(innings, model, b, w, s, target, par, venue, elo1, ipl):
    rich, fitted, calibration = model
    x = features(innings, b, w, s, target, par, venue, elo1, ipl, rich)
    p = sigmoid(calibration[0] + calibration[1] * logit(sigmoid(x @ fitted)))
    if innings == 2:
        p = np.where(target-s == 1, np.maximum(p,0.5), p)
    return p


def pred_frame(d, innings, model):
    return predict(innings, model, *d[["left", "lost_before", "runs_before", *STATIC]].to_numpy().T)


def train_models(d):
    folds, predictions = {}, []
    for year in YEARS:
        history, test = d[d.year.astype(int) < year], d[d.year.astype(int) == year]
        dates = history.match_date.drop_duplicates().sort_values()
        split = dates.iloc[int(len(dates) * 0.76)]
        folds[year] = {}
        for innings in (1, 2):
            fit = history[history.innings.eq(innings) & history.match_date.lt(split)]
            cal = history[history.innings.eq(innings) & history.match_date.ge(split)]
            test_i = test[test.innings.eq(innings)]
            pred = test_i[["match_id", "innings", "year", "group", "y"]].copy()
            for label, rich in (("scoreboard", False), ("venue_team", True)):
                weights = fit_logistic(get_features(fit, innings, rich), fit.y.to_numpy(), nonnegative=(1,2,3), nonpositive=(4,5))
                raw = sigmoid(get_features(cal, innings, rich) @ weights)
                calibration = fit_platt(raw, cal.y.to_numpy())
                model = (rich, weights, calibration)
                folds[year][innings, label] = model
                pred[label] = pred_frame(test_i, innings, model)
            predictions.append(pred)
        print(f"WP fold {year}: {history.match_id.nunique()} prior matches, "
              f"{test.match_id.nunique()} scored, calibration from {split}", flush=True)
    return folds, pd.concat(predictions).sort_index()


def probability_metrics(y, p):
    p = np.clip(p, 0.000001, 0.999999)
    decisive = y != 0.5
    yy = y[decisive]
    ranks = pd.Series(p[decisive]).rank().to_numpy()
    wins, losses = yy.sum(), len(yy) - yy.sum()
    auc = (ranks[yy == 1].sum() - wins * (wins + 1) / 2) / (wins * losses)
    counts = np.bincount(np.minimum((p * 10).astype(int), 9), minlength=10)
    gaps = np.bincount(np.minimum((p * 10).astype(int), 9), weights=p-y, minlength=10)
    return {"events": len(p), "log_loss": float(-np.mean(y * np.log(p) + (1-y) * np.log1p(-p))),
            "brier": float(np.mean(y * (1-p)**2 + (1-y) * p**2)), "auc": float(auc),
            "ece": float(np.abs(gaps).sum() / counts.sum())}


def evaluation(pred):
    stats, calibration = [], []
    for period, p in [("2023–25 forward validation", pred[pred.year.lt("2026")]),
                      ("2026 holdout", pred[pred.year.eq("2026")])]:
        for innings in (0, 1, 2):
            z = p if innings == 0 else p[p.innings.eq(innings)]
            for model in ("scoreboard", "venue_team", "50%"):
                probs = z[model].to_numpy() if model != "50%" else np.full(len(z), 0.5)
                stats.append({"period": period, "innings": innings, "model": model,
                              "matches": z.match_id.nunique(), **probability_metrics(z.y.to_numpy(), probs)})
                for bin_id, c in z.assign(prob=probs, bin=np.minimum((probs*10).astype(int),9)).groupby("bin"):
                    calibration.append((period, innings, model, bin_id, len(c), c.prob.mean(), c.y.mean()))
    choices = [s for s in stats if s["period"].startswith("2023") and s["innings"] == 0 and s["model"] != "50%"]
    selected = min(choices, key=lambda row: row["log_loss"])["model"]
    pd.DataFrame(stats).to_csv(OUT / "wp_validation.csv", index=False)
    pd.DataFrame(calibration, columns=["period","innings","model","probability_decile","events",
                 "predicted","actual"]).to_csv(OUT / "calibration.csv", index=False)
    return selected, stats


def counterfactual(d, models, outcomes):
    innings = int(d.innings.iloc[0])
    b, w, s, target, par, venue, elo1, ipl = d[["left", "lost_before", "runs_before", *STATIC]].to_numpy().T
    pre = predict(innings, models[innings], b,w,s,target,par,venue,elo1,ipl)
    after = np.empty((len(d), len(outcomes)))
    for j, (runs, wicket, legal) in enumerate(outcomes):
        bb, ww, ss = b-legal, w+wicket, s+runs
        finished = (bb <= 0) | (ww >= 10)
        p = predict(innings, models[innings], bb,ww,ss,target,par,venue,elo1,ipl)
        if innings == 2:
            p = np.where(ss >= target, 1, np.where(finished, np.where(ss == target-1, 0.5, 0), p))
        elif finished.any():
            end = finished
            p[end] = 1 - predict(2, models[2], np.full(end.sum(),120), np.zeros(end.sum()),
                                 np.zeros(end.sum()), ss[end]+1, par[end], venue[end], elo1[end], ipl[end])
        after[:, j] = p
    return pre, after


def kernel_lengths(d, opp=None):
    innings = d.innings.to_numpy()
    base_rate = np.where(innings == 1,
                         6*d.runs_before / (120-d.left).clip(lower=1),
                         6*(d.target-d.runs_before) / d.left.clip(lower=1))
    basics = [
        d.ipl.to_numpy(), innings,
        np.searchsorted([7, 13, 25, 37, 61, 91], d.left),
        np.searchsorted([2, 4, 6, 8], d.lost_before),
        np.searchsorted([5, 7, 9, 11, 14, 18, 24], base_rate),
    ]
    if opp is not None:
        basics.append(np.searchsorted([-0.30, -0.12, 0.04, 0.20, 0.38], d[opp]))
    return list(zip(*basics))


def fit_kernel(train, size, opp=None):
    tables = [defaultdict(lambda: np.zeros(size, dtype=int)) for _ in range(7 if opp else 6)]
    keys = kernel_lengths(train, opp)
    for key, outcome in zip(keys, train.outcome):
        for i, table in enumerate(tables):
            table[key[:i]][outcome] += 1
    return tables


def kernel_probs(d, tables, opp=None):
    weights = [0, 100, 100, 125, 90, 85, 110]
    keys = kernel_lengths(d, opp)
    prob_by_key = {}
    for key in set(keys):
        p = tables[0][()] / tables[0][()].sum()
        for i, table in enumerate(tables[1:], 1):
            counts = table.get(key[:i])
            if counts is not None:
                p = (counts + weights[i] * p) / (counts.sum() + weights[i])
        prob_by_key[key] = p
    return np.stack([prob_by_key[key] for key in keys])


def calculate_leverage(d, folds, selected):
    states = d[["runs_total", "is_wicket", "legal"]].astype(int)
    # The support is specified before training. Historically unobserved outcomes have zero weight.
    outcome_tuples = [(runs,wicket,legal) for runs in range(13) for wicket in (0,1) for legal in (0,1)]
    outcome_map = {key: i for i, key in enumerate(outcome_tuples)}
    d["outcome"] = [outcome_map[key] for key in map(tuple, states.to_numpy())]
    checks, blocks = [], []
    for year in YEARS:
        train, test = d[d.year.lt(str(year))], d[d.year.eq(str(year))]
        k = len(outcome_tuples)
        tables = {opp:fit_kernel(train, k, opp) for opp in (None, "bat_quality", "bowl_quality")}
        for innings in (1,2):
            x = test[test.innings.eq(innings)].copy()
            models = {i:folds[year][i, selected] for i in (1,2)}
            pre, after = counterfactual(x, models, outcome_tuples)
            actual = after[np.arange(len(x)), x.outcome.to_numpy()]
            state_probs = kernel_probs(x, tables[None])
            assert np.allclose(state_probs.sum(axis=1), 1)
            average = np.einsum("ij,ij->i", state_probs, after)
            x["wp_before"], x["wp_after"], x["wp_raw"] = pre, actual, actual - pre
            x["leverage"] = np.einsum("ij,ij->i", state_probs, np.abs(after-pre[:,None]))
            x["expected_wpa"] = average - pre
            x["centered_leverage"] = np.einsum("ij,ij->i",state_probs,np.abs(after-average[:,None]))
            x["resid_bat_none"] = actual-average
            x["resid_bowl_none"] = average-actual
            for role, opp, sign in (("bowl","bat_quality",-1),("bat","bowl_quality",1)):
                conditioned = kernel_probs(x, tables[opp], opp)
                x[f"resid_{role}"] = sign * (actual - np.einsum("ij,ij->i", conditioned, after))
            x["legacy_pressure"] = expanded_pressure(x)
            x["switches_innings"] = x.innings.eq(1) & ((x.left-x.legal.astype(int)).eq(0) |
                                    (x.lost_before+x.is_wicket.astype(int)).eq(10))
            if innings == 2:
                end = x.groupby("match_id", sort=False).tail(1)
                exact_terminal = np.isclose(end.wp_after, end.y)
                assert exact_terminal.all(), end.loc[~exact_terminal, ["match_id","wp_after","y"]]
            dot_idx = outcome_map[0,0,1]
            single_idx = outcome_map[1,0,1]
            wicket_idx = outcome_map[0,1,1]
            checks.append({"year": year, "innings": innings, "events": len(x),
                           "mean_coherence_gap_pp": float(100*np.mean(np.abs(average-pre))),
                           "mean_signed_gap_pp": float(100*np.mean(average-pre)),
                           "extra_run_inversion_pct": float(100*np.mean(after[:,single_idx]+1e-7 < after[:,dot_idx])),
                           "wicket_inversion_pct": float(100*np.mean(after[:,wicket_idx] > after[:,dot_idx]+1e-7))})
            blocks.append(x)
        print(f"Counterfactual outcomes and leverage scored for {year}", flush=True)
    z = pd.concat(blocks).sort_index()
    assert z.leverage.between(0,1).all()
    return z, checks, outcome_tuples



def safe_ratio(num, den):
    num, den = np.broadcast_arrays(num, den)
    return np.divide(num, den, out=np.full(num.shape, np.nan), where=den > 0)


def cluster_rows(d, role, mask, weights, residual):
    player = "striker_id" if role == "bat" else "bowler_id"
    x = d.loc[mask, ["match_id", player, "legal", residual]]
    if x.empty:
        return pd.DataFrame(columns=["player","match_id","num","den","events","balls","raw","lev"])
    x = x.assign(player=x[player], num=x[residual]*weights[mask], den=weights[mask],
                 events=1, raw=x[residual], lev=d.loc[mask, "leverage"])
    return x.groupby(["player","match_id"], as_index=False).agg(
        num=("num","sum"), den=("den","sum"), events=("events","size"), balls=("legal","sum"),
        raw=("raw","sum"), lev=("lev","sum"))


def summarize(groups, names, min_balls=60, min_matches=8, ci=False):
    if groups.empty:
        return pd.DataFrame(columns=["player","name","events","balls","fixtures","rating_pp","ci_low","ci_high"])
    data = []
    for p, g in groups.groupby("player"):
        balls, fixtures = int(g.balls.sum()), int(g.balls.gt(0).sum())
        if balls < min_balls or fixtures < min_matches:
            continue
        rating = 100 * g.num.sum()/g.den.sum()
        low, high = np.nan, np.nan
        if ci:
            rng = np.random.default_rng(np.random.SeedSequence([SEED,int(p)]))
            idx = rng.integers(len(g), size=(DRAWS,len(g)))
            values = 100*safe_ratio(g.num.to_numpy()[idx].sum(axis=1), g.den.to_numpy()[idx].sum(axis=1))
            low, high = np.nanquantile(values,[.025,.975])
        data.append((int(p), names.loc[p], int(g.events.sum()), balls, fixtures, rating, low, high))
    result = pd.DataFrame(data, columns=["player","name","events","balls","fixtures","rating_pp","ci_low","ci_high"])
    return result.sort_values(["rating_pp","balls","player"], ascending=[False,False,True]).reset_index(drop=True)


def bh(p):
    indices = np.argsort(p)
    q = np.empty(len(p))
    q[indices] = np.minimum(1,np.minimum.accumulate((p[indices]*len(p)/np.arange(1,len(p)+1))[::-1])[::-1])
    return q


def own_baseline(high, low, names, ranked):
    cols = ["num","den","events","balls","raw","lev"]
    merged = high.merge(low, on=["player","match_id"], how="outer", suffixes=("_hi","_lo")).fillna(0)
    rows = []
    for p,g in merged[merged.player.isin(ranked.player)].groupby("player"):
        nh,nl = int(g.balls_hi.sum()), int(g.balls_lo.sum())
        mh,ml = int(g.balls_hi.gt(0).sum()), int(g.balls_lo.gt(0).sum())
        if min(nh,nl)<60 or min(mh,ml)<8:
            continue
        agg = lambda c: g[c].sum()
        ratio = lambda suffix: 100*agg(f"raw_{suffix}")/agg(f"lev_{suffix}")
        wp = lambda suffix: 100*agg(f"raw_{suffix}")/agg(f"events_{suffix}")
        effect = ratio("hi")-ratio("lo")
        abs_effect = wp("hi")-wp("lo")
        rng = np.random.default_rng(np.random.SeedSequence([SEED,11,int(p)]))
        ix = rng.integers(len(g), size=(DRAWS,len(g)))
        boot_sum = lambda c: g[c].to_numpy()[ix].sum(axis=1)
        h,l = boot_sum("raw_hi"),boot_sum("raw_lo")
        draws = 100*(safe_ratio(h,boot_sum("lev_hi"))-safe_ratio(l,boot_sum("lev_lo")))
        wp_draws = 100*(safe_ratio(h,boot_sum("events_hi"))-safe_ratio(l,boot_sum("events_lo")))
        draws = draws[np.isfinite(draws)]
        ci = np.quantile(draws, [.025,.975])
        wp_ci = np.nanquantile(wp_draws, [.025,.975])
        p_value = min(1.,2*(1+min(np.count_nonzero(draws<=0),np.count_nonzero(draws>=0)))/(1+len(draws)))
        rows.append((p,names.loc[p],nh,nl,mh,ml,ratio("hi"),ratio("lo"),effect,*ci,wp("hi"),wp("lo"),
                     abs_effect,*wp_ci,p_value))
    columns = ["player","name","high_balls","low_balls","high_fixtures","low_fixtures",
               "high_pct_leverage","low_pct_leverage","change_pct_leverage","ci_low","ci_high",
               "high_pp","low_pp","change_pp","change_pp_ci_low","change_pp_ci_high","p"]
    result = pd.DataFrame(rows,columns=columns)
    if len(result):
        result["q_bh"] = bh(result.p.to_numpy())
    return result.sort_values("change_pct_leverage",ascending=False)


def pair_summary(groups, ids, names):
    p1,p2 = ids
    g = groups[groups.player.isin(ids)].pivot(index="match_id",columns="player",
        values=["num","den","events","balls"]).fillna(0)
    if not set(ids).issubset(g.columns.get_level_values(1)):
        return None
    fixture_counts = [int(g["balls"][i].gt(0).sum()) for i in ids]
    scores = [100*g["num"][i].sum()/g["den"][i].sum() for i in ids]
    result = {"names":[names.loc[i] for i in ids],"balls":[int(g["balls"][i].sum()) for i in ids],
              "events":[int(g["events"][i].sum()) for i in ids],"matches":fixture_counts,
              "ratings":scores,"gap_pp":scores[0]-scores[1]}
    if min(fixture_counts)<5:
        return result
    rng = np.random.default_rng(np.random.SeedSequence([SEED,22]))
    ix = rng.integers(len(g),size=(DRAWS,len(g)))
    boot = {p:100*safe_ratio(g["num"][p].to_numpy()[ix].sum(axis=1),g["den"][p].to_numpy()[ix].sum(axis=1)) for p in ids}
    diff = (boot[p1]-boot[p2])
    diff = diff[np.isfinite(diff)]
    result.update({"ci":np.quantile(diff,[.025,.975]).tolist(),"a_above_fraction":float((diff>0).mean())})
    return result


def cohort_profile(d, high):
    u = d.assign(high=high, legacy=d.legacy_pressure)
    profiles = []
    for col in ("innings","phase","group","year","knock_out"):
        for v,g in u.groupby(col,observed=True):
            profiles.append({"grouping":col,"value":str(v),"events":len(g),"high":int(g.high.sum()),
                             "legacy":int(g.legacy.sum()),"mean_leverage_pp":float(100*g.leverage.mean()),
                             "mean_abs_realised_pp":float(100*g.wp_raw.abs().mean())})
    chase = u[u.innings.eq(2)]
    scenarios = [
        ("Late and effectively decided",chase.left.le(18) & (chase.wp_before.lt(.05) | chase.wp_before.gt(.95))),
        ("Late and competitive",chase.left.le(18) & chase.wp_before.between(.35,.65)),
        ("Late, 10+ RRR and two wickets left",chase.left.le(30) & chase.rrr.ge(10) & chase.lost_before.eq(8)),
        ("Late, fair chase below 10 RRR",chase.left.le(30) & chase.rrr.lt(10) & chase.wp_before.between(.35,.65)),
        ("Needs 24–30 runs off 18, at least 3 wickets",chase.left.eq(18) & (chase.target-chase.runs_before).between(24,30)
         & chase.lost_before.le(7)),
        ("Needs 18–27 runs off 18, 0–2 wickets lost",chase.left.eq(18) & (chase.target-chase.runs_before).between(18,27)
         & chase.lost_before.le(2)),
    ]
    out = []
    for label, mask in scenarios:
        g = chase[mask]
        out.append({"scenario":label,"events":len(g),"high":int(g.high.sum()),
                    "median_leverage_pp":float(100*g.leverage.median()) if len(g) else None})
    pd.DataFrame(profiles).to_csv(OUT/"pressure_profile.csv",index=False)
    pd.DataFrame(out).to_csv(OUT/"pressure_scenarios.csv",index=False)
    return profiles,out


def cross_predict(train, test):
    a = train.groupby("player").agg(num=("num","sum"),den=("den","sum"), n=("balls","sum"),
                                    fixtures=("balls",lambda v:v.gt(0).sum()))
    b = test.groupby("player").agg(num=("num","sum"),den=("den","sum"), n=("balls","sum"),
                                   fixtures=("balls",lambda v:v.gt(0).sum()))
    a = a[a.n.ge(60)&a.fixtures.ge(8)]
    b = b[b.n.ge(30)&b.fixtures.ge(4)]
    ab = a.join(b,lsuffix="_train",rsuffix="_test",how="inner")
    if len(ab) < 4:
        return {"common_players":len(ab)}
    x,y = (100*ab[f"num_{s}"]/ab[f"den_{s}"] for s in ("train","test"))
    return {"common_players":len(ab),"historical_rmse_pp":float(np.sqrt(np.mean((x-y)**2))),
            "zero_rmse_pp":float(np.sqrt(np.mean(y**2))),"spearman":float(x.rank().corr(y.rank()))}


def eligible_rows(d):
    # Exclude off-delivery penalty rows and leave wides/no-balls in the event-level WPA.
    return ~d.extras_type.eq("Penalty")


def analyze_players(z, manifest, alternative):
    q25,q50,q70,q75,q80,q90 = z.leverage.quantile([.25,.5,.70,.75,.8,.9])
    high = z.leverage.ge(q75)
    low = z.leverage.le(q50)
    prior_sample = z.year.lt("2026")
    frozen_threshold = z.loc[prior_sample,"leverage"].quantile(.75)
    frozen_high = z.leverage.ge(frozen_threshold)
    by_format_75 = z.groupby("group").leverage.transform(lambda v:v.quantile(.75))
    profiles, scenarios = cohort_profile(z, high)
    z["high"] = high
    z["low"] = low
    year_quantile = z.groupby("year").leverage.transform(lambda v:v.quantile(.75))
    centered = z.centered_leverage.ge(z.centered_leverage.quantile(.75))
    try_format = z.group.eq("IPL")
    innings2 = z.innings.eq(2)
    eligible = eligible_rows(z)
    one = pd.Series(1.,index=z.index)
    legacy = json.loads((ROOT/"output/final_recheck/final_rankings.json").read_text(encoding="utf-8"))
    outputs = {}
    for role,title in (("bowl","Bowlers"),("bat","Batters")):
        p,n=("bowler_id","bowler_name") if role=="bowl" else ("striker_id","striker_name")
        names = z.groupby(p)[n].first()
        res = "resid_"+role
        variants = {
            "Primary": (high,z.leverage,res),
            "Unweighted": (high,one,res),
            "State-only expectation": (high,z.leverage,res+"_none"),
            "Top 30%": (z.leverage.ge(q70),z.leverage,res),
            "Top 20%": (z.leverage.ge(q80),z.leverage,res),
            "Top 10%": (z.leverage.ge(q90),z.leverage,res),
            "Format-specific quartiles":(z.leverage.ge(by_format_75),z.leverage,res),
            "Year-specific quartiles":(z.leverage.ge(year_quantile),z.leverage,res),
            "2024–26, recomputed quartile":(z.year.ge("2024")&z.leverage.ge(z.loc[z.year.ge("2024"),"leverage"].quantile(.75)),z.leverage,res),
            "Centered pre-ball probability":(centered,z.centered_leverage,res),
            "Chase only":(high&innings2,z.leverage,res),
            "First innings only":(high&~innings2,z.leverage,res),
            "IPL only":(high&try_format,z.leverage,res),
            "T20I only":(high&~try_format,z.leverage,res),
            "Legal balls only":(high&z.legal,z.leverage,res),
            "No run-outs, byes or innings changes":(high&~z.dismissal_type.eq("RunOut")&
                          ~z.extras_type.str.contains("bye",case=False,na=False)&~z.switches_innings,z.leverage,res),
            "Old scoreboard flag, unweighted WPA":(z.legacy_pressure,one,res),
            "2026 only, frozen quartile":(frozen_high&~prior_sample,z.leverage,res),
        }
        frames, pools = {}, {}
        for name,(mask,weight,column) in variants.items():
            pools[name] = cluster_rows(z,role,mask&eligible,weight,column)
            frames[name] = summarize(pools[name],names,ci=name in
                                     ("Primary","IPL only","Chase only","First innings only","T20I only"))
        alt_high = alternative.leverage.ge(alternative.leverage.quantile(.75))
        pools["Alternative WP model"] = cluster_rows(alternative,role,alt_high&eligible_rows(alternative),alternative.leverage,res)
        frames["Alternative WP model"] = summarize(pools["Alternative WP model"],names,ci=True)
        primary = frames["Primary"]
        scores = pd.concat([g.assign(analysis=name,rank=np.arange(1,len(g)+1))
                            for name,g in frames.items()],ignore_index=True)
        scores.to_csv(OUT/f"{role}_rankings.csv", index=False, float_format="%.8g")
        primary_idx = set(primary.player.head(10))
        sets = {name:{"eligible":len(g),"overlap":len(primary_idx.intersection(g.player.head(10))),
                         "leader":str(g.name.iloc[0]) if len(g) else None}
                for name,g in frames.items()}
        old_ranks = [x["player"] for x in legacy["roles"][title]["ranking"][:10]]
        primary_groups = pools["Primary"]
        low_groups = cluster_rows(z,role,low&eligible,one,res)
        own = own_baseline(primary_groups,low_groups,names,primary)
        own.to_csv(OUT/f"{role}_own_baseline.csv",index=False,float_format="%.8g")
        own_flags = int(((own.ci_low > 0)|(own.ci_high<0)).sum()) if len(own) else 0
        ranked_own = own[own.q_bh.lt(.05)] if len(own) else own
        train = cluster_rows(z,role,high&prior_sample&eligible,z.leverage,res)
        test = pools["2026 only, frozen quartile"]
        pairs = {}
        if role=="bowl":
            lookup = {n:p for p,n in names.items()}
            ids = [lookup["Jasprit Bumrah"],lookup["Akeal Hosein"]]
            for name in pools:
                pairs[name] = pair_summary(pools[name],ids,names)
            pd.DataFrame([{"analysis":name,**comparison} for name,comparison in pairs.items()
                          if comparison]).to_json(OUT/"bumrah_hosein.json",orient="records",indent=2)
        outputs[role] = {"rankings":json.loads(primary.head(10).to_json(orient="records")),
                         "sensitivities":sets,
                         "old_top10_overlap":len(primary_idx.intersection(old_ranks)),
                         "old_overlap_names":primary[primary.player.isin(set(old_ranks)&primary_idx)].name.tolist(),
                         "own_tested":len(own),"own_ci_excludes_zero":own_flags,"own_fdr":len(ranked_own),
                         "own_fdr_names":ranked_own.name.tolist(),
                         "own_comparison":json.loads(own[own.name.isin(["Jasprit Bumrah","Akeal Hosein"])]
                                                      .to_json(orient="records")),
                         "repeatability":cross_predict(train,test),"pair":pairs}
        print(f"{title}: {len(primary)} eligible, {len(own)} paired baseline comparisons",flush=True)
    manifest.update({"rankings":outputs,"thresholds_pp":{v:float(100*q) for v,q in
                     [("50",q50),("70",q70),("75",q75),("80",q80),("90",q90),("2026_frozen",frozen_threshold)]},
                     "high_events":int(high.sum()),"low_events":int(low.sum()),"events":len(z),
                     "matches":int(z.match_id.nunique()),"legacy_events":int(z.legacy_pressure.sum()),
                     "overlap_events":int((high&z.legacy_pressure).sum()),
                     "alt_overlap":int((high&alternative.leverage.ge(alternative.leverage.quantile(.75))).sum()),
                     "profiles":profiles,"scenarios":scenarios,
                     "period_counts":json.loads(z.groupby("year").agg(events=("match_id","size"),
                               matches=("match_id","nunique"),high=("high","sum")).reset_index().to_json(orient="records"))})
    audit_sample = z[["match_id","match_date","group","innings","innings_ball_num","left","lost_before",
        "runs_before","target","striker_id","bowler_id","legal","wp_before","wp_after","leverage","expected_wpa",
        "resid_bat","resid_bowl","high","low","legacy_pressure"]].copy()
    # The first-innings target is never a model predictor. Suppress it in the scored output.
    audit_sample.loc[audit_sample.innings.eq(1),"target"] = np.nan
    audit_sample.to_csv(OUT/"delivery_audit.csv.gz",index=False,float_format="%.8g")


def main():
    d = build_data()
    folds,pred = train_models(d)
    selected,stats = evaluation(pred)
    print(f"Selected model: {selected}",flush=True)
    z,checks,outcomes = calculate_leverage(d,folds,selected)
    alt = "venue_team" if selected=="scoreboard" else "scoreboard"
    alternative, alt_checks, _ = calculate_leverage(d,folds,alt)
    manifest = {
        "alternative_model":alt,"alternative_coherence":alt_checks,
        "source_sha256":{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((ROOT/"Data Pack").glob("*.csv"))},
        "selected_model":selected,"wp_validation":stats,"coherence":checks,
        "outcome_count":len(outcomes),"outcomes":outcomes and [list(map(int,x)) for x in outcomes],
        "bootstrap_draws":DRAWS,"bootstrap_seed":SEED,
        "screened":json.loads(d.groupby("group").agg(events=("match_id","size"),matches=("match_id","nunique"))
                               .reset_index().to_json(orient="records")),
        "warmup_events":int(d.year.eq("2022").sum()),"warmup_matches":int(d.loc[d.year.eq("2022"),"match_id"].nunique()),
    }
    analyze_players(z,manifest,alternative)
    with (OUT/"results.json").open("w",encoding="utf-8") as f:
        json.dump(manifest,f,indent=2,ensure_ascii=False,allow_nan=False)
    print("Analysis complete",flush=True)


if __name__=="__main__":
    main()


