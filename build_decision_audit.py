"""Audit forecast baselines and apply one transparent scouting decision policy.

This is a retrospective policy revision, not a preregistered experiment.
The supplied Model A rankings stay descriptive; B is a sensitivity comparison.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

from rank_pressure import ROLE_COLUMNS, correlation, per_match, rank, score
from validate_ordinary_prior import BASE, YEARS, fold, predict, rmse

OUT = Path('output')
RNG = np.random.default_rng(151126)
DRAWS = 4000


def records(frame):
    return json.loads(frame.reset_index().to_json(orient='records', double_precision=10))


def correlation_test(prediction, observed):
    x = prediction.rank().to_numpy(float, copy=True)
    y = observed.rank().to_numpy(float, copy=True)
    x -= x.mean()
    y -= y.mean()
    denominator = np.linalg.norm(x) * np.linalg.norm(y)
    observed_rho = float(x @ y / denominator)
    null = np.array([x @ RNG.permutation(y) / denominator for _ in range(20000)])
    return {'spearman': observed_rho,
            'two_sided_permutation_p': float((1 + (np.abs(null) >= abs(observed_rho) - 1e-12).sum()) / 20001)}


def forecast_audit():
    old = json.loads((OUT / 'ordinary_prior_validation.json').read_text())
    result = {'status': 'Retrospective diagnostics; 2026 has been inspected repeatedly.',
              'future_switch_rule': 'Freeze candidate and settings before new data; require a paired 95% RMSE improvement interval above zero against A and zero. Report rank uncertainty; do not veto on an insignificant point-estimate decline.',
              'resamples': DRAWS, 'seed': 151126}
    for role in ROLE_COLUMNS:
        settings = old[role]['metrics']['ordinary_prior']['settings']
        folds = {}
        for year in YEARS:
            frame, games = fold(role, year)
            forecasts = {'zero': pd.Series(0.0, index=frame.index),
                         'ordinary_only': frame.ordinary_prior,
                         'A': predict(frame, BASE), 'B': predict(frame, settings)}
            metrics = {key: {'rmse': rmse(frame, p), 'spearman': None if key == 'zero' else correlation(p, frame.observed)}
                       for key, p in forecasts.items()}
            folds[str(year)] = {'players': len(frame), 'metrics': metrics}
            if year == 2026:
                # Resample whole test fixtures jointly, with predictions/cohort fixed.
                ids = games.index.get_level_values('match_id').unique()
                weights = RNG.multinomial(len(ids), np.full(len(ids), 1 / len(ids)), size=DRAWS).T
                def totals(field):
                    return games[field].unstack(fill_value=0).reindex(index=frame.index, columns=ids, fill_value=0).to_numpy(float) @ weights
                balls = totals('balls')
                targets = np.divide(100 * totals('value'), balls, out=np.full_like(balls, np.nan), where=balls > 0)
                losses = {key: np.sqrt(np.nanmean((p.to_numpy()[:, None] - targets) ** 2, axis=0)) for key, p in forecasts.items()}
                intervals = {}
                for baseline, candidate in [('zero', 'A'), ('A', 'B'), ('zero', 'B'), ('A', 'ordinary_only')]:
                    intervals[f'{baseline}_minus_{candidate}'] = np.quantile(losses[baseline] - losses[candidate], [.025, .975]).tolist()
                ranks = pd.DataFrame(targets).rank(axis=0)
                p = np.broadcast_to(forecasts['A'].to_numpy()[:, None], targets.shape)
                forecast_ranks = pd.DataFrame(np.where(np.isfinite(targets), p, np.nan)).rank(axis=0)
                rhos = ranks.corrwith(forecast_ranks).dropna()
                folds[str(year)].update(rmse_improvement_95=intervals,
                    A_rank_test=correlation_test(forecasts['A'], frame.observed),
                    A_spearman_match_bootstrap_95=rhos.quantile([.025, .975]).tolist())
                for key, saved in [('A', 'current'), ('B', 'ordinary_prior'), ('ordinary_only', 'ordinary_only')]:
                    assert round(metrics[key]['rmse'], 3) == old[role]['metrics'][saved]['holdout_rmse']
        development = {key: float(np.sqrt(np.mean([folds[str(y)]['metrics'][key]['rmse'] ** 2 for y in YEARS[:-1]])))
                       for key in forecasts}
        result[role] = {'folds': folds, 'development_rmse': development, 'B_settings': settings}
        print('FORECAST', role, json.dumps(result[role]), flush=True)
    return result


def decision_evidence():
    saved = json.loads((OUT / 'revised_rankings.json').read_text())
    prior = json.loads((OUT / 'ordinary_prior_validation.json').read_text())
    roster = json.loads((OUT / 'rr_2026_deployment.json').read_text())
    external = pd.read_csv(OUT / 'cross_league/shortlist_external_evidence.csv').set_index('player')
    all_rows, matches_by_role = [], {}
    for role in ROLE_COLUMNS:
        data = score(role)
        pressure = data[data.eligible_event & data.pressure]
        games = per_match(pressure)
        matches_by_role[role] = games
        ranked = rank(games)
        model_a = ranked.rating
        assert ranked.index[:10].tolist() == [r['player'] for r in saved[role]['top']]
        summary = games.groupby(level='player').agg(value=('value','sum'), lift=('lift','sum'), balls=('balls','sum'), matches=('balls','size'))
        names = data.drop_duplicates('player').set_index('player').name
        history = data.groupby('player')[['ordinary_score','ordinary_n']].sum()
        ordinary = 100 * history.ordinary_score / (history.ordinary_n + 60)
        strength = prior[role]['metrics']['ordinary_prior']['settings'][1]
        model_b = (100 * ranked.value + strength * ordinary.reindex(ranked.index)) / (ranked.balls + strength)
        b_order = model_b.rank(method='min', ascending=False)
        roster_key, name_key = ('batting','striker_name') if role == 'Batters' else ('bowling','bowler_name')
        incumbents = {row[name_key] for row in roster[roster_key]}
        by_format = pressure.groupby(['player','group']).agg(balls=('n','sum'), value=('performance','sum'))
        # Include all RR players present in deliveries, even with zero eligible events.
        ids = summary.index.union(names[names.isin(incumbents)].index)
        for player in ids:
            eligible = player in ranked.index
            base = summary.loc[player] if player in summary.index else pd.Series({'value':0, 'lift':0, 'balls':0, 'matches':0})
            row = {'role': role, 'player_id': int(player), 'player': names.loc[player],
                   'is_rr_incumbent': names.loc[player] in incumbents, 'eligible': eligible,
                   'pressure_balls': int(base.balls), 'pressure_matches': int(base.matches),
                   'rating_a': float(model_a.loc[player]) if eligible else None,
                   'rating_b': float(model_b.loc[player]) if eligible else None,
                   'rank_a': int(ranked.index.get_loc(player) + 1) if eligible else None,
                   'rank_b': int(b_order.loc[player]) if eligible else None,
                   'ordinary_rating': float(ordinary.loc[player]),
                   'lift_per100': float(100 * base.lift / base.balls) if base.balls else None}
            if player in games.index.get_level_values('player'):
                sample = games.loc[player]
                positive = sample.value.clip(lower=0)
                best = sample.value.idxmax()
                left = sample.drop(best)
                drop_ok = left.balls.sum() >= 60 and len(left) >= 8
                da = float(100 * left.value.sum() / (left.balls.sum() + 60))
                db = float((100 * left.value.sum() + strength * ordinary.loc[player]) / (left.balls.sum() + strength))
                row.update(best_match_share=float(positive.max() / positive.sum()) if positive.sum() else None,
                    positive_match_share=float(sample.value.gt(0).mean()),
                    drop_best_eligible=bool(drop_ok), drop_best_rating_a=da if drop_ok else None,
                    drop_best_rating_b=db if drop_ok else None,
                    drop_best_rank_a=int(1 + (model_a.drop(player, errors='ignore') > da).sum()) if eligible and drop_ok else None)
            else:
                row.update(best_match_share=None, positive_match_share=None, drop_best_eligible=False,
                           drop_best_rating_a=None, drop_best_rating_b=None, drop_best_rank_a=None)
            row['stable_top10'] = bool(eligible and row['rank_a'] <= 10 and row['drop_best_rank_a'] is not None and row['drop_best_rank_a'] <= 10)
            for fmt in ['IPL','T20I']:
                if (player,fmt) in by_format.index:
                    s = by_format.loc[(player,fmt)]
                    row[fmt+'_balls'], row[fmt+'_per100'] = int(s.balls), float(100*s.value/s.balls) if s.balls else None
                else:
                    row[fmt+'_balls'], row[fmt+'_per100'] = 0, None
            player_name = names.loc[player]
            row['external_qualifies'] = bool(external.loc[player_name].public_qualifies) if player_name in external.index else False
            row['external_per100'] = float(external.loc[player_name].public_per100) if row['external_qualifies'] else None
            # Negative evidence is flagged identically; absence is not a positive result.
            flags = []
            if not eligible: flags.append('Insufficient pressure sample')
            if eligible and not row['stable_top10']: flags.append('Not stable in top 10 after best-match removal')
            for fmt in ['IPL','T20I']:
                rate = row[fmt+'_per100']
                if rate is not None and rate < 0: flags.append(f'Negative {fmt} rate ({row[fmt+"_balls"]} balls)')
            if row['external_per100'] is not None and row['external_per100'] < 0: flags.append('Negative qualified external rate')
            row['flags'] = '; '.join(flags)
            all_rows.append(row)
    evidence = pd.DataFrame(all_rows)
    look = evidence.set_index(['role','player'])
    pairs = [('Batters','Heinrich Klaasen','Shimron Hetmyer'), ('Batters','Dewald Brevis','Shimron Hetmyer'),
             ('Batters','Rinku Singh','Shimron Hetmyer'), ('Batters','Namboori Tilak Varma','Riyan Parag'),
             ('Batters','Shreyas Iyer','Riyan Parag'), ('Bowlers','Josh Hazlewood','Jofra Archer'),
             ('Bowlers','Varun Chakravarthy','Ravi Bishnoi'), ('Bowlers','Rashid Khan','Ravi Bishnoi'),
             ('Bowlers','Wanindu Hasaranga','Ravi Bishnoi'), ('Bowlers','Jason Holder','Sandeep Sharma')]
    comparisons = []
    for role, target, incumbent in pairs:
        t, inc = look.loc[(role,target)], look.loc[(role,incumbent)]
        assert t.eligible and inc.eligible
        margins = {'A': t.rating_a-inc.rating_a, 'B': t.rating_b-inc.rating_b,
                   'drop_A': t.drop_best_rating_a-inc.rating_a,
                   'drop_B': t.drop_best_rating_b-inc.rating_b}
        # Candidate-only removal is deliberately conservative; incumbent stays fixed.
        row = {'role':role,'target':target,'incumbent':incumbent, **{key:float(value) for key,value in margins.items()},
               'positive_in_all_four':bool(all(value > 0 for value in margins.values())),
               'min_margin':float(min(margins.values()))}
        g = matches_by_role[role]
        g = g[g.index.get_level_values('player').isin([int(t.player_id),int(inc.player_id)])]
        ids=g.index.get_level_values('match_id').unique()
        weights=RNG.multinomial(len(ids),np.full(len(ids),1/len(ids)),size=DRAWS).T
        def matrix(field):
            return g[field].unstack(fill_value=0).reindex(index=[int(t.player_id),int(inc.player_id)],columns=ids,fill_value=0).to_numpy(float)
        ratings=100*(matrix('value')@weights)/(matrix('balls')@weights+60)
        row['A_margin_conditional_95']=np.quantile(ratings[0]-ratings[1],[.025,.975]).tolist()
        comparisons.append(row)
    evidence.to_csv(OUT/'decision_player_evidence.csv',index=False,float_format='%.6f')
    policy = {'status':'Retrospective scouting policy, not a forecast or a validated auction price model.',
              'eligibility':'120 prior ordinary balls per event, 60 eligible pressure balls and 8 matches per player.',
              'robustness':'Apply the same candidate-only best-match removal to every target; high-confidence designation requires remaining eligible and top 10. Report all negative format and qualified external rates.',
              'comparison':'Show incumbent A score; check the target advantage under A, B, and removal versions of A and B. Missing incumbent scores remain missing.',
              'priority':'First secure an existing uncovered role; then pursue positive incumbent margins with stable evidence. Domestic status breaks equivalent role-fit choices; do not compare scores between batting and bowling.',
              'availability':'Tiers are acquisition priorities, not assertions that a player will enter the auction.',
              'budget':'No calibrated rupee valuation exists. Allocate by priority tier and stop when an acquisition would leave another required role unfunded.',
              'comparisons':comparisons}
    for pair in comparisons: print('COMPARISON',json.dumps(pair),flush=True)
    print('RR',evidence[evidence.is_rr_incumbent][['role','player','eligible','pressure_balls','pressure_matches','rating_a','rating_b']].to_string(index=False),flush=True)
    return policy


if __name__ == '__main__':
    policy = decision_evidence()
    forecasts = forecast_audit()
    (OUT/'decision_audit.json').write_text(json.dumps({'policy':policy,'forecast':forecasts},indent=2,allow_nan=False),encoding='utf-8')
    print('Saved decision_audit.json and decision_player_evidence.csv',flush=True)
