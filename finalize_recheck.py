"""Freeze the submission order and its audit trail."""
import hashlib
import json
import platform
from pathlib import Path
import numpy as np
import pandas as pd

OUT=Path('output/final_recheck')

def run():
    audit=json.loads((OUT/'audit.json').read_text(encoding='utf-8'))
    result={'date':'2026-11-16','purpose':'Historical pressure-performance ranking; predictive power unproven',
            'ranking_policy':{'cohort':'Worst leave-one-match-out top ten; retain 60 balls and eight positive-exposure matches after every deletion.',
                'order':'Sort by the unrounded worst leave-one-match-out rating, highest first. Exact ties use total qualifying balls, then supplied player ID in ascending order.',
                'sensitivity':'Bootstrap Q25, chase-only results and IPL exposure are supporting evidence.'},'roles':{}}
    for role in ['Batters','Bowlers']:
        all_rows=pd.DataFrame(audit['roles'][role]['ranking']).set_index('player')
        # The audit assigns rank before rounding scores for JSON output.
        selected=all_rows.sort_values('rank').head(10).copy()
        boot=all_rows.sort_values('boot_q0.25_rank')
        chase=pd.DataFrame(audit['roles'][role]['chase_ranking']).set_index('player')
        selected=selected.rename(columns={'rank':'deletion_rank'})
        selected.insert(0,'final_rank',range(1,11))
        selected.to_csv(OUT/(role.lower()+'_submission_order.csv'),index_label='player')
        final_ids=set(selected.index)
        checks={
            'chase_overlap':len(final_ids & set(chase.index[:10])),
            'chase_refit_overlap':len(final_ids & set(x['player'] for x in audit['roles'][role]['chase_refit_ranking'][:10])),
            'bootstrap_q25_overlap':len(final_ids & set(boot.index[:10])),
            'equal_eight_match_bootstrap_overlap':len(final_ids & set(all_rows.sort_values('equal8_q25_rank').index[:10])),
        }
        result['roles'][role]={'checks':checks,
            'ranking':json.loads(selected.reset_index().round(6).to_json(orient='records',force_ascii=False))}
        assert len(selected)==10 and selected.index.is_unique
        assert selected.final_rank.tolist()==selected.deletion_rank.tolist()==list(range(1,11))
    # Joint fixture resampling preserves any fixture overlap. There is none for this pair.
    games=pd.read_csv(OUT/'bowlers_match_evidence.csv')
    # Keep the reported score difference oriented as Bumrah minus Hosein.
    leaders=result['roles']['Bowlers']['ranking'][:2][::-1]
    assert [p['name'] for p in leaders]==['Jasprit Bumrah','Akeal Hosein']
    ids=[p['player'] for p in leaders]
    pair=games[games.player.isin(ids)]
    fixtures=np.sort(pair.match_id.unique());count=len(fixtures)
    draws=np.random.default_rng(161126).multinomial(count,np.repeat(1/count,count),size=20000)
    def matrix(column):
        return pair.pivot(index='player',columns='match_id',values=column).reindex(index=ids,columns=fixtures).fillna(0).to_numpy()
    scores=100*(draws@matrix('value').T)/(60+draws@matrix('balls').T)
    difference=scores[:,0]-scores[:,1]
    result['leading_bowler_joint_resample']={'players':[p['name'] for p in leaders], 'draws':20000,
        'fixtures':count,'positive_exposure_matches':[p['matches'] for p in leaders],
        'shared_fixtures':len(set(pair[pair.player.eq(ids[0])].match_id)&set(pair[pair.player.eq(ids[1])].match_id)),
        'first_above_second_frequency':float((difference>0).mean()),
        'difference_2p5_50_97p5':np.quantile(difference,[.025,.5,.975]).tolist(),
        'scope':'Conditional resampling of fixed adjusted contributions, not a probability of future superiority.'}
    result['data_hashes']={str(p).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(Path('Data Pack').glob('*.csv'))}
    result['runtime']={'python':platform.python_version(),'pandas':pd.__version__,'numpy':np.__version__}
    (OUT/'final_rankings.json').write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf-8')
    a,b=[result['roles'][role]['ranking'] for role in ['Batters','Bowlers']]
    pd.DataFrame([{'Rank':i+1,'Batter':x['name'],'Bowler':y['name']} for i,(x,y) in enumerate(zip(a,b))]).to_csv(OUT/'Unstop_Submission_Order.csv',index=False)
    for role in ['Batters','Bowlers']:
        print(role, result['roles'][role]['checks'])
        print([(r['final_rank'],r['name']) for r in result['roles'][role]['ranking']])
    print(result['leading_bowler_joint_resample'])

if __name__=='__main__':run()
