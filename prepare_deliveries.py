import pandas as pd
import numpy as np
from pathlib import Path
from pandas.testing import assert_series_equal
src = Path("Data Pack")
def read(name):
    return pd.read_csv(src / (name + ".csv"), keep_default_na=False, na_values=[""])
m=read("matches").merge(read("competitions"),on="comp_id",validate="m:1")
m["group"]=np.select([m.comp_name.str.fullmatch(r"IPL \d{4}"),m.match_format.eq("T20I")],["IPL","T20I"],default="Emerging T20")
m["year"]=m.match_date.str[:4]
b=read("ball_by_ball").merge(m,on="match_id",validate="m:1").sort_values(["match_id","innings","innings_ball_num"])
b["runs_total"]=b.runs+b.extras1_runs+b.extras_2_runs
b["legal"]=~b.extras_type.isin(["Overstep","wide","other","Penalty"])
b["bat_ball"]=~b.extras_type.isin(["wide","Penalty"])
b["bowl_event"]=~b.extras_type.eq("Penalty")
b["bat_out"]=b.is_wicket & b.striker_id.eq(b.dismissed_player_id) & ~b.dismissal_type.eq("Retire Out")
b["bowl_wicket"]=b.dismissal_type.isin(["Stump","Caught","LBW","Bowled","Hit Wicket"])
b["bowl_runs"]=b.runs+b.extras1_runs.where(b.extras_type.isin(["Overstep","wide","other"]),0)
innings=b.groupby(["match_id","innings"],sort=False)
for target,raw in [("runs_before","runs_total"),("legal_before","legal"),("lost_before","is_wicket")]:
    b[target]=innings[raw].cumsum()-b[raw]
assert_series_equal((b.legal_before+b.legal).groupby([b.match_id,b.innings]).max(),innings.legal.sum(),check_names=False)
b["left"]=120-b.legal_before
summary=innings.agg(score=("runs_total","sum"),wk=("is_wicket","sum"),legal=("legal","sum"),team=("batting_team_id","first"))
s1=summary.xs(1,level=1).add_suffix("1")
s2=summary.xs(2,level=1).add_suffix("2")
a=m.set_index("match_id").join(s1).join(s2)
a["score_diff"]=a.score1-a.score2
a["defended"]=a.score_diff.gt(0)
a["chased"]=a.score_diff.lt(0)
a["rain"]=a[["first_inn_revised_overs","second_inn_revised_overs","revised_target"]].notna().any(axis=1)|a.result.str.contains(r"\b(?:d/l|dls|duckworth)\b",case=False,regex=True)
a["expected_winner"]=np.select([a.chased,a.defended],[a.team2,a.team1],default=np.nan)
a["win_by_runs"]=pd.to_numeric(a.result.str.extract(r"(?i)won\s*(?:by\s*)?(\d+)\s*runs?",expand=False),errors="coerce")
a["win_by_wk"]=pd.to_numeric(a.result.str.extract(r"(?i)won\s*(?:by\s*)?(\d+)\s*w(?:icket|kt)s?",expand=False),errors="coerce")
a["margin_disagrees"]=(a.win_by_runs.notna() & a.win_by_runs.ne(a.score_diff))|(a.win_by_wk.notna() & a.win_by_wk.ne(10-a.wk2))
a["budget_flag"]=a.legal1.gt(120)|a.legal2.gt(120)|(a.legal1.lt(120)&a.wk1.lt(10))|(a.defended&a.legal2.lt(120)&a.wk2.lt(10))
regular=b[b.innings.le(2)]
overs=regular.groupby(["match_id","innings","overid"]).legal.agg(["sum","size"]).reset_index()
last_over=overs.groupby(["match_id","innings"]).overid.transform("max")
bad_over=overs.overid.lt(last_over)&overs["sum"].ne(6)
a["bad_over"]=a.index.isin(overs.loc[bad_over,"match_id"])
a["both"]=a.score1.notna()&a.score2.notna()
a["ok_result"]=(a.expected_winner.eq(a.win_team_id)|a.score_diff.eq(0))&~a.margin_disagrees
a["is_clean"]=a.group.ne("Emerging T20")&a.both & a.win_team_id.notna() & ~a.rain & ~a.budget_flag & ~a.bad_over & a.ok_result
f=b[b.match_id.isin(a[a.is_clean].index)&b.innings.le(2)].copy()
f["phase"]=pd.cut(f.overid,[0,6,15,20],labels=["Powerplay","Middle","Death"])
f["needed"]=f.match_id.map(a.score1)+1-f.runs_before
f["rrr"]=6*f.needed/f.left
f["won"]=f.batting_team_id.eq(f.win_team_id)

