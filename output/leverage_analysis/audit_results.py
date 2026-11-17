"""Independently reconcile the report and compare stricter leaderboard screens."""
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
R=json.loads((HERE/"results.json").read_text(encoding="utf-8"))
d=pd.read_csv(HERE/"delivery_audit.csv.gz")
assert len(d)==R["events"]==144089
assert d.match_id.nunique()==R["matches"]==604
assert d.high.sum()==R["high_events"]
assert (d.high&d.legacy_pressure).sum()==R["overlap_events"]
assert np.isclose(d.leverage.quantile(.75)*100,R["thresholds_pp"]["75"],atol=1e-6)
assert d.loc[d.innings.eq(1),"target"].isna().all()
assert not d.duplicated(["match_id","innings","innings_ball_num"]).any()
for filename,digest in R["source_sha256"].items():
    assert hashlib.sha256((ROOT/"Data Pack"/filename).read_bytes()).hexdigest()==digest
z=d[d.high].copy()
# Raw source identification of off-delivery penalties is independent of model grouping.
source=pd.read_csv(ROOT/"Data Pack"/"ball_by_ball.csv",usecols=["match_id","innings","innings_ball_num","extras_type"])
key=["match_id","innings","innings_ball_num"]
excluded=source[source.extras_type.eq("Penalty")][key].drop_duplicates()
z=z.merge(excluded.assign(off_delivery=True),on=key,how="left",validate="one_to_one")
z=z[z.off_delivery.isna()]
summary={}
for role,id_col in (("bowl","bowler_id"),("bat","striker_id")):
    rank=pd.read_csv(HERE/f"{role}_rankings.csv")
    rank=rank[rank.analysis.eq("Primary")].set_index("player")
    x=z.assign(weighted=z.leverage*z[f"resid_{role}"])
    g=x.groupby([id_col,"match_id"]).agg(weighted=("weighted","sum"),den=("leverage","sum"),
                                       balls=("legal","sum"),events=("legal","size")).reset_index()
    rows=[]
    for p, row in rank.iterrows():
        q=g[g[id_col].eq(p)]
        num,den=q.weighted.to_numpy(),q.den.to_numpy()
        assert q.balls.sum()==row.balls and q.events.sum()==row.events and q.balls.gt(0).sum()==row.fixtures
        rate=100*num.sum()/den.sum()
        assert np.isclose(rate,row.rating_pp,atol=1e-6)
        rng=np.random.default_rng(np.random.SeedSequence([R["bootstrap_seed"],int(p)]))
        ids=rng.integers(len(q),size=(R["bootstrap_draws"],len(q)))
        score=100*num[ids].sum(axis=1)/den[ids].sum(axis=1)
        low,q25,hi=np.quantile(score,[.025,.25,.975])
        assert np.isclose(low,row.ci_low,atol=1e-6) and np.isclose(hi,row.ci_high,atol=1e-6)
        loo=min(100*(num.sum()-num)/(den.sum()-den))
        rows.append((int(p),row["name"],int(row.balls),int(row.fixtures),rate,q25,loo,low,hi))
    c=pd.DataFrame(rows,columns=["player","name","balls","fixtures","rating_pp","bootstrap_q25",
                                  "worst_fixture_deletion","ci_low","ci_high"])
    c.to_csv(HERE/f"{role}_reliability.csv",index=False,float_format="%.8g")
    selections={"120 balls and 12 matches":c[c.balls.ge(120)&c.fixtures.ge(12)].nlargest(10,"rating_pp"),
                "Bootstrap Q25":c.nlargest(10,"bootstrap_q25"),
                "Worst match removed":c.nlargest(10,"worst_fixture_deletion")}
    primary=set(c.head(10).player)
    summary[role]={k:{"top10_overlap":len(primary&set(v.player)),"leader":str(v.name.iloc[0]),
                        "leader_balls":int(v.balls.iloc[0]),"leader_score":float(v.rating_pp.iloc[0])}
                   for k,v in selections.items()}
pair=R["rankings"]["bowl"]["pair"]["Primary"]
reported=pd.read_csv(HERE/"bowl_rankings.csv")
for player,rating,balls in zip(pair["names"],pair["ratings"],pair["balls"]):
    p=int(reported.loc[reported.name.eq(player),"player"].iloc[0])
    x=z[z.bowler_id.eq(p)]
    assert x.legal.sum()==balls
    assert np.isclose(100*np.average(x.resid_bowl,weights=x.leverage),rating,atol=1e-6)
(HERE/"reliability_checks.json").write_text(json.dumps(summary,indent=2),encoding="utf-8")
print("Hashes, grains, screens, both player cohorts, all primary intervals and featured pair reconciled.")


