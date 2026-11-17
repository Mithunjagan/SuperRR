"""Render the SupeRR leverage report from the analysis outputs."""
import csv
import json
import math
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib.colors import HexColor, white
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import Paragraph

HERE = Path(__file__).resolve().parent
R = json.loads((HERE/"results.json").read_text(encoding="utf-8"))
REL = json.loads((HERE/"reliability_checks.json").read_text(encoding="utf-8"))
P = HERE.parent/"pdf"/"SupeRR_Leverage_Analysis.pdf"
P.parent.mkdir(exist_ok=True)
W,H = A4
M=42
CW=W-2*M
INK=HexColor("#13243D")
MUTED=HexColor("#435670")
INDIGO=HexColor("#313D83")
TEAL=HexColor("#087F7A")
LINE=HexColor("#DDE4EF")
PALE=HexColor("#EAF4F3")
LIGHT=HexColor("#F3F5FA")
c=Canvas(str(P),pagesize=A4,pageCompression=1)
c.setTitle("SupeRR | Cricket pressure as leverage")
c.setAuthor("SupeRR")
page_n=0
y=0

def txt(s,x,yy,size=10,font="Helvetica",color=INK):
    c.setFillColor(color)
    c.setFont(font,size)
    c.drawString(x,yy,s)

def right(s,x,yy,size=10,font="Helvetica",color=INK):
    c.setFillColor(color)
    c.setFont(font,size)
    c.drawRightString(x,yy,s)

def paragraph(s,width=CW,x=M,size=10.5,leading=15,color=INK,after=11):
    global y
    style=ParagraphStyle("copy",fontName="Helvetica",fontSize=size,leading=leading,textColor=color)
    item=Paragraph(s,style)
    _,h=item.wrap(width,1000)
    item.drawOn(c,x,y-h)
    y-=h+after

def page(num,title,sub):
    global y,page_n
    if page_n:
        assert y>=55,(page_n,y)
        c.showPage()
    page_n=num
    c.setFillColor(INDIGO)
    c.rect(0,H-11,W,11,stroke=0,fill=1)
    txt("SupeRR",M,H-38,14,"Helvetica-Bold",INDIGO)
    right("ROUND 1  /  METHODOLOGY STUDY",W-M,H-37,8,"Helvetica-Bold",MUTED)
    txt(title,M,H-82,26,"Helvetica-Bold")
    y=H-96
    paragraph(sub,size=10.5,leading=14,color=MUTED,after=17)
    c.setStrokeColor(LINE)
    c.line(M,46,W-M,46)
    txt("SUPPLIED DATA PACK   |   IPL AND T20I   |   16 NOVEMBER 2026",M,30,8,"Helvetica",MUTED)
    right(f"{num:02d} / 06",W-M,30,8,"Helvetica-Bold",INDIGO)

def heading(s):
    global y
    txt(s,M,y-12,13,"Helvetica-Bold",INDIGO)
    y-=22

def table(headers,rows,widths,align=None,fs=9.5,rh=23):
    global y
    widths=[v*CW/sum(widths) for v in widths]
    align=align or ["l"]+["r"]*(len(headers)-1)
    for j,row in enumerate([headers,*rows]):
        top=y-j*rh
        c.setFillColor(INDIGO if j==0 else (LIGHT if j%2 else white))
        c.rect(M,top-rh,CW,rh,stroke=0,fill=1)
        x=M
        for col,(val,width,a) in enumerate(zip(row,widths,align)):
            label=str(val)
            font="Helvetica-Bold" if j==0 or col==0 else "Helvetica"
            color=white if j==0 else INK
            if c.stringWidth(label,font,fs)>width-14:
                raise ValueError(f"Table cell {label!r} is too wide for {width:.0f}")
            (txt if a=="l" else right)(label,x+7 if a=="l" else x+width-7,top-rh*.65,fs,font,color)
            x+=width
    y-=(len(rows)+1)*rh+12

def callout(label,body):
    global y
    item=Paragraph(body,ParagraphStyle("panel",fontName="Helvetica",fontSize=11,leading=15,textColor=INK))
    _,h=item.wrap(CW-32,1000)
    height=h+48
    c.setFillColor(PALE)
    c.roundRect(M,y-height,CW,height,9,stroke=0,fill=1)
    txt(label,M+16,y-22,12,"Helvetica-Bold",TEAL)
    item.drawOn(c,M+16,y-34-h)
    y-=height+15

def pp(x,d=2): return f"{x:+.{d}f}"
def nums(x): return f"{x:,}"
def ci(x): return f"[{pp(x[0])}, {pp(x[1])}]"
def sign(x): return "higher" if x>0 else "lower"
def ratio(k,n): return f"{100*k/n:.1f}%"
def val(period,innings,model):
    return next(v for v in R["wp_validation"] if v["period"].startswith(period)
                and v["innings"]==innings and v["model"]==model)

B=R["rankings"]["bowl"]
A=R["rankings"]["bat"]
PA=B["pair"]["Primary"]
IPL=B["pair"]["IPL only"]
winner="Bumrah" if PA["gap_pp"]>0 else "Hosein"
years=R["period_counts"]
hi=R["high_events"]
q75=R["thresholds_pp"]["75"]
sc=R["scenarios"]
first,chase=(next(r for r in R["profiles"] if r["grouping"]=="innings" and r["value"]==str(i)) for i in (1,2))
interval_note = ("The interval includes zero." if PA["ci"][0] <=0<= PA["ci"][1]
                 else "The conditional interval excludes zero in the pooled sample.")
def primary_name(key):
    return {"scoreboard":"Scoreboard + format","venue_team":"Venue + team strength","50%":"50% baseline"}[key]
pmodel=R["selected_model"]
amodel=R["alternative_model"]

def gap_chart():
    global y
    subsets=[("All qualifying matches",PA),("IPL only",IPL),("Chase only",B["pair"]["Chase only"])]
    lo=math.floor(min(-1,min(p["ci"][0] for _,p in subsets)))
    hi=math.ceil(max(1,max(p["ci"][1] for _,p in subsets)))
    x1,x2=M+148,W-M-25
    x=lambda v:x1+(v-lo)/(hi-lo)*(x2-x1)
    top=y-4
    for tick in range(lo,hi+1):
        c.setStrokeColor(LINE if tick else MUTED)
        c.setLineWidth(.7 if tick else 1.05)
        c.line(x(tick),top,x(tick),top-64)
        right(str(tick),x(tick)+3,top-77,8,color=MUTED)
    for i,(label,p) in enumerate(subsets):
        yy=top-12-19*i
        txt(label,M,yy-3,9,color=MUTED)
        c.setStrokeColor(TEAL)
        c.setFillColor(TEAL)
        c.setLineWidth(2)
        c.line(x(p["ci"][0]),yy,x(p["ci"][1]),yy)
        c.circle(x(p["gap_pp"]),yy,3,stroke=0,fill=1)
    y=top-90
    paragraph("Bumrah minus Hosein, percentage points per delivery. Markers show estimates and lines show 95% fixture-bootstrap intervals.",
              size=8.8,leading=12,color=MUTED,after=13)

page(1,"Cricket pressure as leverage",
     "A delivery-level analysis of match stakes, performance above expectation and changes from each player's ordinary baseline.")
callout("Bumrah vs Hosein", f"<b>{winner} leads on pooled leverage-weighted WPA.</b> "
        f"Bumrah scored {pp(PA['ratings'][0])} and Hosein {pp(PA['ratings'][1])} percentage points per delivery above expectation. "
        f"The Bumrah-minus-Hosein gap was {pp(PA['gap_pp'])}, with a 95% fixture-bootstrap interval of {ci(PA['ci'])}. {interval_note}")
gap_chart()
heading("What the analysis found")
rows=[
    ["Later matches scored",f"{nums(R['matches'])} matches",f"{nums(R['events'])} deliveries"],
    ["High leverage",f"{nums(hi)} deliveries",f"{q75:.3f} pp threshold"],
    ["Bowling value leader",B["rankings"][0]["name"],f"{pp(B['rankings'][0]['rating_pp'])} pp"],
    ["Batting value leader",A["rankings"][0]["name"],f"{pp(A['rankings'][0]['rating_pp'])} pp"],
]
table(["Measure","Result","Exposure or scale"],rows,[185,162,150],["l","l","r"],rh=25)
paragraph(f"The leverage rule picks up {nums(sc[1]['high'])} of {nums(sc[1]['events'])} deliveries in close chases with 18 balls or fewer "
          f"according to the model's pre-ball odds. It picks up {nums(sc[0]['high'])} of {nums(sc[0]['events'])} late deliveries "
          f"in effectively decided chases. A late over and a high required rate have different meanings at different scores.")
paragraph(f"The ranking remains sensitive to the definition. The original SupeRR top ten overlaps this leaderboard for "
          f"{B['old_top10_overlap']}/10 bowlers and {A['old_top10_overlap']}/10 batters. The results on page 5 show what changes "
          f"when the probability model, pressure cutoff or sample changes.")
heading("How to read the numerical results")
paragraph("A positive score means the player generated more win probability than the model expected from an average player "
          "in comparable situations. The own-baseline check on page 6 asks whether the same player produced more or less value "
          "per unit of leverage as the stakes rose. Both use historical observations of play.",after=0)

page(2,"01  Build and test win probability",
     "The probability is for the team batting at that state. A regulation tie receives a 0.5 outcome.")
paragraph(f"The original pack supplied 883 matches and 200,999 delivery rows. The original screening rules retained 771 IPL and "
          f"T20I matches with 184,476 regulation delivery rows. That excluded Emerging T20, revised fixtures, irreconcilable "
          f"scorecards and Super Overs. The {R['warmup_matches']} matches in 2022 seeded training and supplied no ranked events.")
paragraph("Each annual fit used earlier years only. A later block within that training history was held back for probability "
          "calibration. Venue par, format par and team-strength ratings used earlier calendar dates for every match. Neither "
          "probability model used the current batter or bowler's identity.")
heading("Chronological model comparison")
wp=[]
for period in ("2023","2026"):
    for k in (pmodel,amodel,"50%"):
        v=val(period,0,k)
        wp.append([period if period=="2026" else "2023-25",primary_name(k),f"{v['log_loss']:.3f}",
                   f"{v['brier']:.3f}",f"{v['auc']:.3f}",f"{100*v['ece']:.1f} pp"])
table(["Test","Model","Log loss","Brier","AUC","Cal. error"],wp,[66,161,66,65,57,85],["l","l","r","r","r","r"],rh=22)
paragraph("Lower log loss, Brier and calibration error are better. Higher AUC is better. The 50% baseline can have a small "
          "calibration error because it issues one probability close to the overall win rate. It cannot distinguish game states.",
          size=9.5,leading=13,color=MUTED)
heading("Why the probability model matters")
v1,v2=(val("2026",i,pmodel) for i in (1,2))
paragraph(f"First innings used a projected total relative to historical par, with the observed scoring pace shrunk toward par "
          f"and projected remaining runs reduced for wickets lost. The chase model used runs needed, balls left and wickets. "
          f"The expanded candidate added venue-specific par and prior team strength. The primary model was fixed by 2023-25 "
          f"log loss. On the 2026 holdout, its first-innings AUC was {v1['auc']:.3f}, versus {v2['auc']:.3f} in chases.")
check = max(r["mean_coherence_gap_pp"] for r in R["coherence"])
run_inv = max(r["extra_run_inversion_pct"] for r in R["coherence"])
wicket_inv = max(r["wicket_inversion_pct"] for r in R["coherence"])
paragraph(f"Fitted score and wicket effects were constrained to have the expected direction within an innings. Every observed "
          f"chase-ending ball reconciled with its regulation result. Across innings and years, the largest average discrepancy "
          f"between pre-ball probability and expected post-ball probability was {check:.2f} pp. Counterfactual one-run reversals "
          f"peaked at {run_inv:.2f}% and wicket reversals at {wicket_inv:.2f}% in any fold. The first-to-second innings transition "
          f"uses a separately fitted model, so exact state-by-state consistency is limited.", after=0)

page(3,"02  Measure the stakes before the ball",
     "Leverage is the expected absolute change in win probability across possible delivery outcomes.")
paragraph("For each pre-ball state, estimate a distribution over <b>total runs, wickets and whether a legal ball was consumed</b>. "
          "The distribution uses earlier matches and shrinks sparse bins toward broader groups, from format and innings through "
          "balls left, wickets lost and scoring demand. This includes dots, singles, boundaries, wickets, and illegal deliveries.")
paragraph("<b>Leverage = sum of outcome probability x |post-outcome win probability - pre-ball win probability|.</b> "
          "For a hypothetical first-innings ending, evaluate the chase start with the new target and switch team perspective. "
          "In a terminal chase state the post-ball probability is 1, 0.5 or 0. The outcome actually observed does not set the flag.")
heading("Sanity checks from observed pre-ball states")
scenario_rows=[[v["scenario"].replace("Late, fair chase", "Late, competitive chase").replace("left","in hand"),
                nums(v["events"]), ratio(v["high"],v["events"]),f"{v['median_leverage_pp']:.2f}"]
               for v in sc[:5]]
table(["Scenario","Events","Flagged","Median pp"],scenario_rows,[283,64,75,80],fs=9,rh=24)
paragraph("Competitive means 35%-65% pre-ball chase win probability. Effectively decided means below 5% or above 95%. The first two rows use 18 balls or fewer.",size=9.3,leading=13,color=MUTED)
heading("A global quartile changes who gets counted")
paragraph(f"The {q75:.3f} pp cutoff flags {ratio(first['high'],first['events'])} of first-innings events and "
          f"{ratio(chase['high'],chase['events'])} of chase events. It overlaps the old scoreboard rule on "
          f"{nums(R['overlap_events'])} deliveries, representing {ratio(R['overlap_events'],hi)} of leverage flags and "
          f"{ratio(R['overlap_events'],R['legacy_events'])} of the old rule's flags over the same 2023-26 sample.")
rows=[[r["year"],nums(r["matches"]),nums(r["events"]),nums(r["high"]),ratio(r["high"],r["events"])] for r in years]
table(["Year","Matches","Scored events","High leverage","Flagged share"],rows,[64,85,122,112,111],rh=22)
paragraph("A pooled cutoff is comparable on the model's probability scale, but changing model fits and match mixtures produce "
          "unequal flag shares over time. The sensitivity runs use year-specific quartiles, omit the earliest scored year and "
          "recompute leverage around expected post-ball odds.",after=0)

page(4,"03  Rank contribution above expectation",
     "All eligible IPL and T20I events, 2023-26. Rates and intervals are percentage points of win probability per delivery.")
paragraph("Batter WPA is the change in the batting team's odds. Bowler WPA reverses that sign. The expected value conditions "
          "on the state and uses the opponent's earlier format-adjusted runs and dismissals as a quality proxy. "
          "<b>Rating = sum of leverage x (observed WPA - expected WPA) divided by sum of leverage.</b>")
paragraph("Players need at least 60 legal high-leverage balls across eight matches. Wides and no-balls contribute to the "
          "rate and the delivery-event count, while off-delivery penalty rows are excluded from player ratings. Intervals "
          "resample whole fixtures 6,000 times and hold the fitted model and cohort fixed.",size=9.5,leading=13)
for title,sample in (("Bowlers",B),("Batters",A)):
    heading(title)
    rows=[[f"{i}  {r['name']}",nums(r["balls"]),nums(r["fixtures"]),pp(r["rating_pp"]),
           ci((r["ci_low"],r["ci_high"]))] for i,r in enumerate(sample["rankings"],1)]
    table(["Player","Legal balls","Matches","WPA above exp.","95% fixture interval"],rows,
          [176,66,60,91,119],fs=9,rh=18.5)
paragraph("Sort order uses point estimates. Wide intervals and a low minimum sample can leave the apparent leaders separated "
          "by very little evidence. Winner selection is also excluded from the interval calculation.",size=9.2,leading=12,after=0)

page(5,"04  Test how the rankings change",
     "The pair comparison gives both player estimates, exposure and a shared-fixture bootstrap for their difference.")
heading("Jasprit Bumrah vs Akeal Hosein")
cutset=["Primary","IPL only","Chase only","Alternative WP model","Year-specific quartiles","2024-26, recomputed quartile"]
label={"Primary":"All, primary","IPL only":"IPL only","Chase only":"Chase only",
       "Alternative WP model":"Venue and team model" if amodel=="venue_team" else "Scoreboard model",
       "Year-specific quartiles":"Year-specific quartiles","2024-26, recomputed quartile":"2024-26 only"}
lookup={k.replace("–","-"):v for k,v in B["pair"].items()}
rows=[]
for k in cutset:
    p=lookup[k]
    if p:
        rows.append([label[k],f"{pp(p['ratings'][0])} / {p['balls'][0]}",f"{pp(p['ratings'][1])} / {p['balls'][1]}",
                     pp(p["gap_pp"]),ci(p["ci"]) if "ci" in p else "Sparse"])
table(["Analysis","Bumrah pp / balls","Hosein pp / balls","Gap pp","95% gap interval"],rows,
      [133,91,91,54,115],fs=8.9,rh=22)
paragraph(f"Bumrah leads in {ratio(PA['a_above_fraction'],1)} of pooled fixture resamples. The frequency describes this sample. "
          f"The IPL pair uses {IPL['matches'][0]} and {IPL['matches'][1]} fixtures. The eight-match IPL leaderboard "
          "screen is applied separately.")
heading("Top-ten membership vs the primary ranking")
keys=["Unweighted","State-only expectation","Top 30%","Top 20%","Top 10%","Format-specific quartiles",
      "Year-specific quartiles","Centered pre-ball probability","Chase only","IPL only","Alternative WP model"]
rows=[]
for key in keys:
    b,a=B["sensitivities"][key],A["sensitivities"][key]
    rows.append([key,f"{b['overlap']}/10",f"{a['overlap']}/10",f"{b['eligible']} / {a['eligible']}"])
table(["Sensitivity","Bowlers kept","Batters kept","Eligible B / A"],rows,[217,92,92,100],fs=9,rh=19)
paragraph(f"The two probability models agree on {ratio(R['alt_overlap'],hi)} of primary high-leverage events. "
          f"With at least 120 legal high-leverage balls across 12 matches, {REL['bowl']['120 balls and 12 matches']['leader']} "
          f"leads bowling and {REL['bat']['120 balls and 12 matches']['leader']} leads batting. "
          f"Ranking by bootstrap Q25 puts {REL['bowl']['Bootstrap Q25']['leader']} and "
          f"{REL['bat']['Bootstrap Q25']['leader']} first. The "
          "supporting tables also show first-innings and T20I-only splits, legal-only results and a check excluding run-outs, "
          "byes and innings changes.",size=9.4,leading=13,after=0)

page(6,"05  Test each player's own baseline",
     "A pressure-performance rating and a change from ordinary performance answer different questions.")
paragraph("Compare the top quartile with the bottom half of leverage. In each band, divide the sum of unweighted WPA over "
          "expectation by the sum of leverage. This expresses value as a share of the average swing available. Also compute "
          "the difference in raw adjusted WPA per delivery, where small low-leverage events can have smaller absolute effects. "
          "Both bands need 60 legal balls and eight matches. Resample their shared fixture set together.")
rows=[]
for v in B["own_comparison"]:
    rows.append([v["name"],f"{v['high_balls']} / {v['low_balls']}",pp(v["change_pct_leverage"]),
                 ci((v["ci_low"],v["ci_high"])),f"{v['q_bh']:.3f}"])
table(["Bowler","High / low balls","Change","95% interval","FDR q"],rows,[120,102,75,128,68],rh=23)
paragraph(f"{B['own_ci_excludes_zero']} of {B['own_tested']} bowlers and {A['own_ci_excludes_zero']} of {A['own_tested']} "
          f"batters have nominal 95% intervals that exclude zero. After false-discovery adjustment within role, "
          f"{B['own_fdr']} bowling and {A['own_fdr']} batting results pass q &lt; 0.05. "
          "The change can reflect match roles, opponents and game states as well as performance. The data does not measure temperament.")
heading("Do the player ratings repeat in 2026?")
rows=[]
for label,sample in [("Bowlers",B),("Batters",A)]:
    rt=sample["repeatability"]
    rows.append([label,rt["common_players"],f"{rt.get('historical_rmse_pp',math.nan):.2f}",
                 f"{rt.get('zero_rmse_pp',math.nan):.2f}",f"{rt.get('spearman',math.nan):+.2f}"])
table(["Role","Players","Historical RMSE","Zero RMSE","Spearman"],rows,[99,65,120,105,83],rh=23)
paragraph("The evaluation uses pre-2026 player ratings, the pre-2026 leverage cutoff and the common eligible 2026 sample. "
          "Zero predicts no value above the state and opponent expectation. This test measures player-rating repeatability, "
          "which is distinct from the model's accuracy at predicting a team's result.")
heading("Inputs, reproducibility and limits")
paragraph("Source inputs were the six supplied SupeRR CSVs. The existing Round 1 dossier and final rankings supply the original "
          "comparison. Run <font name='Courier'>python output/leverage_analysis/run_analysis.py</font> from the project root "
          "with NumPy and pandas. The companion archive includes source code, input SHA-256 hashes, probability diagnostics, "
          "player rankings and uncertainty tables. Fixture intervals omit probability-model and threshold estimation uncertainty. "
          "Team-level WPA can include fielding and non-striker effects. The model has no pitch, weather or knockout stakes multiplier.",
          size=9.5,leading=13,after=0)
assert y>=55,(page_n,y)
c.save()
print(P)




