"""Recheck the revised pressure ranking without changing delivery scores.

Whole-player-match bootstrap, fixed-window filtering, full chase re-estimation,
and 2026 diagnostics. All resampling is conditional on the fitted scores.
"""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
from audit_match_reliability import expanded_pressure, deletion_ranking, metrics
from rank_pressure import score, per_match, f, CUTOFF, ROLE_COLUMNS

SEED = 161126
DRAWS = 20000
OUT = Path('output/final_recheck')

def resample(games, player, size=None):
    games = games.sort_index()
    v, n = games.value.to_numpy(), games.balls.to_numpy()
    count = len(games) if size is None else size
    rng = np.random.default_rng(np.random.SeedSequence([SEED, int(player), count]))
    pick = rng.integers(len(games), size=(DRAWS, count))
    return 100 * v[pick].sum(axis=1) / (60 + n[pick].sum(axis=1))

def records(frame):
    return json.loads(frame.reset_index().round(6).to_json(orient='records',force_ascii=False))

def summary(data, names):
    table = deletion_ranking(data, names)
    games = per_match(data)
    draws = {}
    for player in table.index:
        g = games.loc[player]
        draws[player] = z = resample(g, player)
        for q in [.025,.10,.25,.50,.75,.975]:
            table.loc[player, f'boot_q{q:g}'] = np.quantile(z,q)
        table.loc[player,'equal8_q25'] = np.quantile(resample(g, player,8),.25)
        table.loc[player,'min_balls_after_removal'] = g.balls.sum()-g.balls.max()
        table.loc[player,'min_matches_after_removal'] = g.balls.gt(0).sum()-1
        table.loc[player,'min_match_value'] = g.value.min()
        table.loc[player,'worst_match_removed'] = int((100*(g.value.sum()-g.value)/(60+g.balls.sum()-g.balls)).idxmin())
    for key in ['boot_q0.25','boot_q0.1','equal8_q25']:
        order = table.sort_values([key,'balls','player'],ascending=[False,False,True])
        table[key+'_rank'] = pd.Series(np.arange(1,len(order)+1),index=order.index)
    return table, draws

def chase_pressure(d):
    return expanded_pressure(d) & d.innings.eq(2)

def run():
    OUT.mkdir(parents=True,exist_ok=True)
    result={'seed':SEED,'draws':DRAWS,'cutoff':CUTOFF,'events':len(f),'matches':int(f.match_id.nunique()),
            'pressure_events':int(expanded_pressure(f).sum()),'roles':{}}
    old=json.load(open(OUT/'reference_before_recheck.json',encoding='utf-8'))
    for role in ROLE_COLUMNS:
        print('SCORING',role,flush=True)
        d=score(role,pressure_selector=expanded_pressure)
        names=d.drop_duplicates('player').set_index('player').name
        eligible=d[d.pressure & d.eligible_event]
        t, draws=summary(eligible,names)
        assert t.name.head(10).tolist()==[r['name'] for r in old[role]['proposed']['ranking'][:10]]
        np.testing.assert_allclose(t.score.head(10),[r['score'] for r in old[role]['proposed']['ranking'][:10]],atol=.00005)
        splits=[]
        for (p,fmt,inn),g in eligible.groupby(['player','group','innings']):
            splits.append({'player':p,'name':names.loc[p],'format':fmt,'innings':inn,'balls':int(g.n.sum()),
                           'matches':int(g.loc[g.n.gt(0),'match_id'].nunique()),'adjusted_value':g.performance.sum(),
                           'runs':g.runs.sum(),'charged_runs':g.bowl_runs.sum(),'bowler_wickets':int(g.bowl_wicket.sum())})
        pd.DataFrame(splits).to_csv(OUT/(role.lower()+'_splits.csv'),index=False)
        for label,sub in [('chase',eligible[eligible.innings.eq(2)]),('collapse',eligible[eligible.innings.eq(1)]),
                          ('ipl',eligible[eligible.group.eq('IPL')]),('t20i',eligible[eligible.group.eq('T20I')])]:
            g=per_match(sub).groupby(level='player').agg(balls=('balls','sum'),matches=('balls',lambda x:int(x.gt(0).sum())),value=('value','sum'))
            for col in ['balls','matches','value']:
                t[label+'_'+col]=g[col].reindex(t.index,fill_value=0)
        chase, _=summary(eligible[eligible.innings.eq(2)],names)
        # Refit ordinary history after reclassifying all collapse deliveries as ordinary.
        only=score(role,pressure_selector=chase_pressure)
        rescored,_=summary(only[only.pressure & only.eligible_event],names)
        for label,table in [('chase',chase),('chase_refit',rescored)]:
            t[label+'_rank']=table['rank'].reindex(t.index)
            t[label+'_boot_rank']=table['boot_q0.25_rank'].reindex(t.index)
        # Same-pool rank frequencies; eligible players held fixed; independent player match draws.
        player_ids=list(t.index)
        matrix=np.stack([draws[p] for p in player_ids])
        ranks=(-matrix).argsort(axis=0).argsort(axis=0)+1
        t['bootstrap_top10_frequency']=(ranks<=10).mean(axis=1)
        t['bootstrap_top1_frequency']=(ranks==1).mean(axis=1)
        final_order=t.sort_values(['boot_q0.25','balls','player'],ascending=[False,False,True])
        top=set(final_order.index[:10])
        cross={
            'loo_vs_bootstrap_overlap':len(set(t.index[:10])&top),
            'loo_chase_overlap':len(set(t.index[:10])&set(chase.index[:10])),
            'bootstrap_chase_overlap':len(top&set(chase.sort_values('boot_q0.25_rank').index[:10])),
            'bootstrap_chase_refit_overlap':len(top&set(rescored.sort_values('boot_q0.25_rank').index[:10])),
            'bootstrap_chase_loo_overlap':len(top&set(chase.index[:10])),
            'bootstrap_q10_overlap':len(top&set(t.sort_values('boot_q0.1_rank').index[:10])),
            'equal8_overlap':len(top&set(t.sort_values('equal8_q25_rank').index[:10])),
        }
        freeze=score(role,cutoff=CUTOFF,pressure_selector=expanded_pressure)
        usable=freeze[freeze.pressure & freeze.eligible_event]
        train,_=summary(usable[usable.match_date.lt(CUTOFF)],names)
        test=per_match(usable[usable.match_date.ge(CUTOFF)]).groupby(level='player').agg(value=('value','sum'),balls=('balls','sum'),matches=('balls','size'))
        test=test[test.balls.ge(12)&test.matches.ge(3)]
        test=test.loc[test.index.intersection(train.index)]
        observed=100*test.value/test.balls
        forward={'players':len(test),'loo':metrics(train.score,observed),'pooled':metrics(train.pooled,observed),
                 'bootstrap_q25':metrics(train['boot_q0.25'],observed),'zero':metrics(pd.Series(0.,index=test.index),observed)}
        t.to_csv(OUT/(role.lower()+'_audit.csv'),index_label='player')
        per_match(eligible).reset_index().merge(names.rename('name'),on='player').to_csv(OUT/(role.lower()+'_match_evidence.csv'),index=False)
        result['roles'][role]={'eligible':len(t),'checks':cross,'forward':forward,'ranking':records(t),
                               'chase_ranking':records(chase),'chase_refit_ranking':records(rescored)}
        if role=='Bowlers':
            h=t.index[t.name.eq('Akeal Hosein')][0]; b=t.index[t.name.eq('Jasprit Bumrah')][0]
            result['hosein_bumrah']={'independent_bootstrap_bumrah_gt_hosein':float((draws[b]>draws[h]).mean()),
                                    'difference_quantiles':np.quantile(draws[b]-draws[h],[.025,.25,.5,.75,.975]).tolist()}
            raw=d[d.pressure & d.player.eq(h)]
            result['hosein_raw']={'balls':int(raw.n.sum()),'charged_runs':float(raw.bowl_runs.sum()),
                                  'economy':float(6*raw.bowl_runs.sum()/raw.n.sum()),
                                  'cold_balls_removed':int(raw.loc[~raw.eligible_event,'n'].sum())}
        print(role,cross,forward,flush=True)
        print(t[['name','score','boot_q0.25','boot_q0.25_rank','equal8_q25_rank','chase_balls','chase_matches','chase_rank','chase_boot_rank','chase_refit_boot_rank']].head(16).round(3).to_string(index=False),flush=True)
    (OUT/'audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(result.get('hosein_bumrah'),result.get('hosein_raw'),flush=True)

if __name__=='__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    run()
