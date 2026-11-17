"""Render the dossier from the verified scouting evidence."""
import argparse
import csv
import json
from datetime import date
from html import escape
from math import ceil
from pathlib import Path

from reportlab.graphics.shapes import Drawing, Line, Rect, Circle, String
from reportlab.lib.colors import HexColor, white
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Table, TableStyle

out = Path("output")
def read(name):
    return json.loads((out / name).read_text(encoding="utf-8"))

with (out / "scouting_player_evidence.csv").open(encoding="utf-8", newline="") as handle:
    evidence = list(csv.DictReader(handle))
top = {role: [row for row in evidence if row["role"] == role and int(row["rank"]) <= 10]
       for role in ("Batters", "Bowlers")}
rr = read("rr_2026_deployment.json")
ranks = read("revised_rankings.json")
prior = read("ordinary_prior_validation.json")
experiment_d = read("role_pressure_validation.json")
decision_audit = read("decision_audit.json")
with (out / "decision_player_evidence.csv").open(encoding="utf-8", newline="") as handle:
    decision_rows = list(csv.DictReader(handle))
decision = {(r["role"], r["player"]): r for r in decision_rows}
comparisons = {r["target"]: r for r in decision_audit["policy"]["comparisons"]}

def rating(role, player):
    row = decision[(role, player)]
    return f"{float(row['rating_a']):+.2f}" if row["rating_a"] else f"Ineligible: {row['pressure_balls']} balls"

def margin(player, key="A"):
    return f"{comparisons[player][key]:+.2f}"

def interval(values):
    return f"[{values[0]:+.2f}, {values[1]:+.2f}]"
ink, muted, pink, blue, teal, pale, grid = map(HexColor, [
    "#17253A", "#43546D", "#A31857", "#235D88", "#16776B", "#EFF3F7", "#CCD7E3"])
styles = {}
for name, size, leading, color, bold, space in [
    ("tag",9,13,pink,True,8), ("title",28,32,ink,True,8), ("intro",11,15.5,muted,False,12),
    ("head",13,17,ink,True,5), ("body",10.2,14.3,ink,False,9), ("note",8.8,12.2,muted,False,7),
    ("cell",8.6,11,ink,False,0), ("th",8.1,10,white,True,0),
]:
    styles[name] = ParagraphStyle(name, fontName="Helvetica-Bold" if bold else "Helvetica",
        fontSize=size, leading=leading, textColor=color, spaceAfter=space,
        spaceBefore=8 if name in ("head","note") else 0)
story = []

def text(value, style="body"):
    story.append(Paragraph(value, styles[style]))

def page(title, intro):
    if story:
        story.append(PageBreak())
    text("SUPERR SELECTOR  /  RAJASTHAN ROYALS  /  15 NOVEMBER 2026", "tag")
    text(title, "title")
    text(intro, "intro")

def section(title, body):
    text(title,"head")
    text(body)

def table(headers, data, widths, padding=5):
    rows = [[Paragraph(value, styles["th"]) for value in headers]]
    rows.extend([Paragraph(escape(str(value)), styles["cell"]) for value in row] for row in data)
    tab = Table(rows, colWidths=widths, repeatRows=1, hAlign="LEFT")
    tab.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0),ink), ("ROWBACKGROUNDS",(0,1),(-1,-1),[white,pale]),
        ("VALIGN",(0,0),(-1,-1),"MIDDLE"), ("TOPPADDING",(0,0),(-1,-1),padding),
        ("BOTTOMPADDING",(0,0),(-1,-1),padding),
    ]))
    story.append(tab)

def link(label, url):
    return f'<link href="{url}" color="#235D88">{label}</link>'

def pct(value):
    return f"{float(value):.0%}"

def scatter():
    d=Drawing(480,180)
    def x(v): return 46 + (v-14)*18.4
    def y(v): return 28 + (v-.45)*255
    for v in (.5,.6,.7,.8,.9):
        d.add(Line(46,y(v),451,y(v),strokeColor=grid,strokeWidth=.5))
        d.add(String(39,y(v)-3,pct(v),textAnchor="end",fontSize=8,fillColor=muted))
    for v in (15,20,25,30,35):
        d.add(String(x(v),15,str(v),textAnchor="middle",fontSize=8,fillColor=muted))
    d.add(String(46,167,"Matches with positive adjusted value",fontSize=8.5,fillColor=muted))
    d.add(String(250,1,"Model A rating",textAnchor="middle",fontSize=8.5,fillColor=muted))
    labels={"Dewald Brevis":("Brevis",-7,-12,"end"),"Heinrich Klaasen":("Klaasen",8,6,"start"),
            "Rashid Khan":("Rashid",-7,9,"end"),"Jofra Archer":("Archer",8,-10,"start")}
    for role,rows in top.items():
        for row in rows:
            px,py=x(float(row["rating"])),y(float(row["positive_match_share"]))
            if role=="Batters":
                d.add(Circle(px,py,3.7,fillColor=pink,strokeColor=None))
            else:
                d.add(Rect(px-3.2,py-3.2,6.4,6.4,fillColor=blue,strokeColor=None))
            if row["player"] in labels:
                label,dx,dy,anchor=labels[row["player"]]
                d.add(String(px+dx,py+dy,label,textAnchor=anchor,fontSize=8,fontName="Helvetica-Bold",fillColor=ink))
    d.add(Circle(328,170,3.3,fillColor=pink,strokeColor=None))
    d.add(String(335,167,"Batters",fontSize=8,fillColor=muted))
    d.add(Rect(387,167,6,6,fillColor=blue,strokeColor=None))
    d.add(String(398,167,"Bowlers",fontSize=8,fillColor=muted))
    return d

def phase_chart():
    d=Drawing(480,221)
    phases=(("Powerplay",blue),("Middle",teal),("Death",pink))
    for i,(phase,color) in enumerate(phases):
        x=126+i*88
        d.add(Rect(x,206,9,8,fillColor=color,strokeColor=None))
        d.add(String(x+13,206,phase,fontSize=8,fillColor=muted))
    for balls in (0,100,200,300):
        x=126+.86*balls
        d.add(Line(x,23,x,198,strokeColor=grid,strokeWidth=.45))
        d.add(String(x,12,str(balls),textAnchor="middle",fontSize=8,fillColor=muted))
    for i,row in enumerate(rr["bowling"][:8]):
        y=187-i*21
        d.add(String(118,y,row["bowler_name"],textAnchor="end",fontSize=8.7,fillColor=ink))
        x=126
        for phase,color in phases:
            balls=row[phase]
            width=.86*balls
            if balls:
                d.add(Rect(x,y-2,width,9,fillColor=color,strokeColor=None))
                if width>=19:
                    d.add(String(x+width/2,y,str(balls),textAnchor="middle",fontSize=7,fillColor=white))
            x+=width
        d.add(String(x+5,y,str(row["Total"]),fontSize=8,fillColor=muted))
    d.add(String(250,0,"Legal deliveries for Rajasthan Royals",textAnchor="middle",fontSize=8.5,fillColor=muted))
    return d


def public_match_chart(matches, players):
    drawing = Drawing(488, 222)
    tick_step = 10
    extent = max(abs(float(row["adjusted_value"])) for row in matches)
    limit = max(tick_step, 5 * ceil(extent / 5))
    tick_limit = tick_step * (limit // tick_step)
    for i, player in enumerate(players):
        panel_x = 250 * (i % 2)
        panel_y = 114 * (1 - i // 2)
        left, right = panel_x + 31, panel_x + 232
        zero = panel_y + 52
        scale = 42 / limit
        drawing.add(String(left, panel_y + 103, player, fontSize=10, fontName="Helvetica-Bold", fillColor=ink))
        for tick in range(-tick_limit, tick_limit + 1, tick_step):
            y = zero + scale * tick
            drawing.add(Line(left, y, right, y, strokeColor=grid if tick else muted,
                             strokeWidth=.45 if tick else .7))
            if i % 2 == 0:
                drawing.add(String(left - 5, y - 2.5, str(tick), textAnchor="end", fontSize=8, fillColor=muted))
        sample = sorted((r for r in matches if r["player"] == player), key=lambda r: (r["match_date"], r["cricsheet_match_id"]))
        bar_step = (right - left) / len(sample)
        bar_width = min(10, .68 * bar_step)
        for j, row in enumerate(sample):
            value = float(row["adjusted_value"])
            center = left + (j + .5) * bar_step
            height = scale * value
            color = teal if value >= 0 else pink
            if abs(height) < 1:
                drawing.add(Circle(center, zero + height, 1.08, fillColor=color, strokeColor=None))
            else:
                drawing.add(Rect(center - bar_width / 2, min(zero, zero + height), bar_width, abs(height),
                                 fillColor=color, strokeColor=None))
    return drawing


def external_panel(folder):
    with (folder / "shortlist_external_evidence.csv").open(encoding="utf-8", newline="") as handle:
        shortlist = {row["player"]: row for row in csv.DictReader(handle)}
    with (folder / "highlighted_player_matches.csv").open(encoding="utf-8", newline="") as handle:
        matches = list(csv.DictReader(handle))
    validation = json.loads((folder / "validation.json").read_text(encoding="utf-8"))
    number_qualifying = sum(row["public_qualifies"] == "True" for row in shortlist.values())
    players = ("Dewald Brevis", "Heinrich Klaasen", "Rashid Khan", "Sunil Narine")
    page("External league validation",
         f"{validation['external_matches']:,} Cricsheet matches in BBL, PSL, SA20 and CPL yielded "
         f"{validation['external_pressure_deliveries']:,} pressure deliveries. {number_qualifying} of {len(shortlist)} picks "
         "qualified for comparison. The fixture audit found zero overlaps with the supplied pack.")
    text("Adjusted contribution in each match (run equivalents)", "head")
    story.append(public_match_chart(matches, players))
    text("Each mark is one match, in date order within each player. Zero is the expected value for that league, match state "
         "and opponent. Both roles use the same vertical scale.", "note")

    rows = []
    for player in players:
        sample = shortlist[player]
        worst = min((row for row in matches if row["player"] == player), key=lambda row: float(row["adjusted_value"]))
        rows.append([player, sample["public_leagues"],
                     f"{int(float(sample['public_balls']))} / {int(float(sample['public_matches']))}",
                     int(float(sample["public_positive_matches"])), f"{float(sample['public_per100']):+.2f}",
                     f"{float(sample['public_lift_per100']):+.2f}",
                     f"{float(worst['adjusted_value']):+.2f} / {worst['pressure_balls']}"])
    table(["Player", "League", "Balls /<br/>matches", "Positive<br/>matches", "Adjusted<br/>per 100",
           "Lift vs own<br/>play per 100", "Worst value<br/>/ balls"], rows, [91,86,57,49,55,69,81], 4)
    narine = [row for row in matches if row["player"] == "Sunil Narine"]
    cpl_balls = sum(int(row["pressure_balls"]) for row in narine if row["league"] == "CPL")
    total_balls = sum(int(row["pressure_balls"]) for row in narine)
    text("Qualification uses 120 prior ordinary balls and an external sample of at least 12 pressure balls in three matches. "
         f"Brevis's evidence comes from SA20. The CPL accounts for {cpl_balls} of Narine's {total_balls} balls.", "note")

    rashid = [row for row in matches if row["player"] == "Rashid Khan"]
    values = [float(row["adjusted_value"]) for row in rashid]
    gains = [value for value in values if value > 0]
    losses = [value for value in values if value < 0]
    worst = min(rashid, key=lambda row: float(row["adjusted_value"]))
    worst_value = float(worst["adjusted_value"])
    remaining_balls = sum(int(row["pressure_balls"]) for row in rashid) - int(worst["pressure_balls"])
    without_worst = 100 * (sum(values) - worst_value) / remaining_balls
    when = date.fromisoformat(worst["match_date"]).strftime("%d %b %Y")
    counterexamples = [f"{name} ({float(shortlist[name]['public_per100']):+.2f})" for name in ("Tim David", "Naveen ul Haq")]
    text(f"<b>Rashid's downside.</b> {len(gains)} positive matches added {sum(gains):+.2f}. "
         f"{len(losses)} negative matches contributed {sum(losses):+.2f}. "
         f"His worst was {worst_value:+.2f} against {escape(worst['opponent'])} on {when} "
         f"({worst['role_runs']} runs and {worst['role_wickets']} wickets in {worst['pressure_balls']} pressure balls). "
         f"Omitting that match moves his adjusted rate to {without_worst:+.2f} per 100. "
         f"{' and '.join(counterexamples)} also had negative adjusted rates per 100.", "body")

    metrics = validation["roles"]
    bat, bowl = (metrics[role]["transfer"]["2026"] for role in ("Batters", "Bowlers"))
    text(f"<b>Rank transfer and forecast test.</b> The 2026 public test compared {bat['comparable_players']} batters "
         f"(Spearman {bat['spearman']:+.2f}) and {bowl['comparable_players']} bowlers ({bowl['spearman']:+.2f}) "
         "using pre-2026 ratings. Comparable samples were small throughout 2024-26.", "body")
    trials = [metrics[role]["public_challenger"] for role in ("Batters", "Bowlers")]
    table(["2026 forecast holdout", "Model A RMSE", "With public prior RMSE", "Model A / public Spearman"], [
        [role, f"{t['holdout_rmse_model_a']:.2f}", f"{t['holdout_rmse_with_public']:.2f}",
         f"{t['holdout_spearman_model_a']:.3f} / {t['holdout_spearman_with_public']:.3f}"]
        for role, t in zip(("Batters", "Bowlers"), trials)
    ], [128,100,127,133], 4)
    text("2024-25 selected prior weights: batting 0 (identical to A); bowling 0.75 (uncertain improvement). "
         + link("Cricsheet data", "https://cricsheet.org/downloads/") + "; "
         + link("ODC-BY 1.0", "https://cricsheet.org/licensing/") + ".", "note")


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--external-validation", type=Path, help="Directory with scored Cricsheet evidence")
parser.add_argument("--output", type=Path, default=out / "pdf/SupeRR Round 1 Scouting Dossier.pdf")
args = parser.parse_args()


page("Rajasthan Royals scouting dossier",
     "Decision: pursue Klaasen for overseas batting and Varun for domestic spin. If Archer leaves, fund the pace replacement first.")
section("Headline pick: Heinrich Klaasen",
        f"Prioritise Klaasen over an overseas finisher replacement: {rating('Batters','Heinrich Klaasen')} versus Hetmyer's "
        f"{rating('Batters','Shimron Hetmyer')}. The advantage stays positive under Model B and after removing Klaasen's best match. "
        "He was positive in 18 of 23 matches; his best supplied 16% of positive value and its removal leaves him fourth.")
text("<b>Reliable in this sample; not established as a pressure specialist.</b> His lift over ordinary play is only +2.5 per 100, "
     "his T20I rate is -5.3 on 17 balls, and SA20 lift is -6.3 despite a positive adjusted rate. Ferreira is ineligible "
     "(11 balls); a superiority claim over Ferreira is unavailable.","note")
table(["Priority","Target / incumbent A rating","Decision and evidence"],[
    ["1 | Batting","Klaasen +30.48 / Hetmyer -1.47",
     "First overseas batting target. Rinku is the domestic fallback; Brevis is an upside watchlist option."],
    ["2 | Domestic spin","Varun +29.19 / Bishnoi -15.13",
     "First spin target, ahead of Rashid. Positive in both formats; stays fifth without his best match; uses no overseas slot."],
    ["1 if Archer leaves | Pace","Hazlewood +30.97 / Archer +15.17",
     "First replacement for the powerplay/death role. Positive margin survives four specifications, but T20I rate is -12.0 on 48 balls."],
],[89,151,248],5)
section("Ratings are noisy; acquisition priority follows robustness",
        "The 2026 rank correlations are 0.40 (14 batters) and 0.22 (16 bowlers); permutation p-values are 0.156 and 0.415. "
        "External rank transfer is negative on just six batters and three bowlers. Model A does not reliably beat a zero forecast. "
        "These are historical scouting signals, not proven predictions of future wins.")
section("What the recommendation rules out",
        "Do not pay a pressure premium for Iyer or Brevis: both leave the top ten without their best match. Do not make Rashid "
        "the spin priority: his external rate is -8.27 per 100, including a -19.64 worst match. Archer is a squad-coverage decision; "
        "his rating is tenth and falls to fifteenth without his best match.")
text("<b>Model choice:</b> A measures adjusted contribution under pressure; B adds ordinary ability and is used as a sensitivity check. "
     "B won five of six reported metrics. Retaining A reflects what we measure, not better forecasting. <b>Future switching rule:</b> "
     "freeze a candidate before fresh data; require a positive 95% RMSE-improvement interval against A and zero. This rule is "
     "declared now, not claimed to be preregistered. Full decisions and validation are on pages 6-8.","note")

page("How the pressure rating works","Model A ranks historical adjusted contribution under pressure; lift answers the separate usual-performance question.")
section("Sample and pressure situations",
        "The data contains 184,476 regulation delivery events from 771 screened matches (352 IPL, 419 T20I) from 2022 to 2026. Of 883 "
        "match records, 30 were emerging tournaments, 16 lacked deliveries, 38 had revision indicators, 15 lacked both innings or a "
        "complete result, and 13 failed reconciliation. Exclusions are sequential. Super Overs are excluded.")
text("A chase qualifies before the ball with 1 to 30 legal balls remaining, 8 to 16 required runs per over and at least two wickets in hand. "
     "A first-innings delivery qualifies when at least three wickets have fallen before 60 legal balls. Together those rules identify "
     "14,381 delivery events before role and player filters.")
section("Actual and expected contribution",
        "Batters earn runs off the bat minus dismissal cost. Bowlers earn credited wicket value minus charged runs, including wides and "
        "no-balls, with exposure counted in legal balls. Powerplay, middle and death wickets are worth 8, 6 and 4 run equivalents. "
        "Run-outs earn no bowling wicket credit. Batting exposure omits wides and off-delivery penalties.")
text("The batting and bowling expectations use earlier dates only. Within each format, innings and phase, the model adjusts for balls "
     "remaining, wickets lost and required run rate or first-innings current run rate. The opposing striker or bowler's earlier ordinary "
     "residual in the same format, innings and phase supplies the opponent adjustment.")
section("Ranking and eligibility",
        "<b>Rating = 100 × sum of actual minus expected value ÷ (eligible pressure balls + 60).</b> An event counts after the player has "
        "120 ordinary balls of history. Ranking requires 60 pressure balls across eight matches. Lift compares pressure residuals with the "
        "player's ordinary adjusted rate and remains outside the headline rating.")
text("Reproduction details","head")
text("Balls-left groups are six balls within the last 30 and 12 balls earlier. Wicket cut points are 1, 2, 3, 4, 6 and 9 lost. Rate bands "
     "are two runs per over, capped at 30. The starting phase reference uses 100 virtual balls at +1 for batting and -1 for bowling. "
     "The two state levels borrow 100 and 60 balls from their parent estimates. Opponent and ordinary-player rates use 60 virtual "
     "balls toward zero. The one-run primary extra marked “other” is treated as a no-ball. Retire-outs are excluded from batting dismissal cost.","note")

for role in ("Batters","Bowlers"):
    page(f"Top 10 {role.lower()}",f"{ranks[role]['eligible']} players met the Model A eligibility criteria.")
    rows=[]
    for r in top[role]:
        rows.append([r["rank"],r["player"],f"{float(r['rating']):.2f}",r["pressure_balls"],r["pressure_matches"],
                     pct(r["positive_match_share"]),pct(r["best_match_share"]),f"{float(r['worst_match_value']):+.1f}",
                     pct(r["bootstrap_top10_share"])])
    table(["Rank","Player","Rating","Balls","Games","Positive<br/>games","Best<br/>share","Worst<br/>match","Top 10<br/>share"],
          rows,[36,111,43,35,40,55,50,58,60],4)
    text("Best share is the biggest match's share of all positive adjusted value. Worst match is the lowest observed total in run equivalents "
         "and reflects opportunity as well as performance. Top-ten frequencies use 1,000 whole-match resamples with baselines and eligibility fixed.","note")
    text("Format exposure, ordinary-play lift and best-match sensitivity","head")
    lift = {str(row["player"]): row["lift_per100"] for row in ranks[role]["top"]}
    rows=[]
    for r in top[role]:
        fmt=[]
        for name in ("IPL","T20I"):
            rate=r[name+"_residual_per100"]
            fmt.append(f"{r[name+'_pressure_balls']} / {float(rate):+.1f}" if rate else "0 / —")
        after=f"No. {int(float(r['drop_best_rank']))}" if r["drop_best_rank"] else "Ineligible"
        rows.append([r["player"],*fmt,f"{lift[r['player_id']]:+.1f}",after])
    table(["Player","IPL balls /<br/>value per 100","T20I balls /<br/>value per 100","Lift vs ordinary<br/>per 100","Rank without<br/>best match"],
          rows,[128,92,92,91,85],4)
    text("Rates are unshrunk run equivalents per 100 pressure balls. Lift measures the difference from the player's ordinary adjusted "
         "rate. The removal test holds other players' scores fixed.","note")

page("Where a signing would help",
     f"Actual deployment in {rr['matches']} screened Royals IPL 2026 matches. The chart covers the eight most-used bowlers.")
story.append(phase_chart())
text("Incumbent comparison: the same eligibility rule for everyone", "head")
incumbent_rows = []
for role, name in [("Batters","Shimron Hetmyer"),("Batters","Donovan Ferreira"),("Batters","Dhruv Jurel"),
                   ("Batters","Riyan Parag"),("Bowlers","Jofra Archer"),("Bowlers","Nandre Burger"),
                   ("Bowlers","Sandeep Sharma"),("Bowlers","Ravi Bishnoi"),("Bowlers","Ravindra Jadeja"),
                   ("Bowlers","Yash Punja")]:
    r=decision[(role,name)]
    incumbent_rows.append([name,role,f"{r['pressure_balls']} / {r['pressure_matches']}",
                           rating(role,name),f"{float(r['rating_b']):+.2f}" if r['rating_b'] else "Ineligible"])
table(["RR player","Discipline","Balls / games","Model A","Model B"],incumbent_rows,[130,66,81,131,80],3)
text("Ratings use all eligible supplied IPL/T20I history, not just RR's 2026 matches. Ineligible means fewer than 60 eligible "
     "pressure balls or eight matches; it does not mean poor ability. Jurel has 55 balls in eight matches, Ferreira 11 in one.","note")
text("<b>Role allocation.</b> Jurel occupied No. 3 in all 15 screened matches; Parag used No. 4 in 10 of 13 appearances. "
     "Keep that structure unless deliberately reopening a top-four role. Ferreira and Hetmyer cover Nos. 4-6. Archer's 198 "
     "powerplay and 102 death balls make his departure a coverage problem. Spin already has 462 middle-over balls across "
     "Jadeja, Punja and Bishnoi: Varun is an upgrade choice, not an empty-role claim.","body")
text("Deployment measures usage, not phase quality. "+link("Official RR 2026 squad","https://www.rajasthanroyals.com/rr-players")+".","note")

page("A consistent decision mechanism",
     "P1 = pursue first for the stated role; P2 = fallback or reopened role; P3 = watchlist; R = retention; X = benchmark only.")
text("<b>1. Fix the role.</b> Prioritise an uncovered powerplay/death role if Archer leaves; otherwise fund the batting upgrade "
     "before additional spin. <b>2. Check the incumbent.</b> Require a positive advantage under A, B and candidate-only "
     "best-match removal; do not fill missing ratings with zero. <b>3. Apply the same robustness test.</b> A leading target "
     "must remain eligible and top ten after removal. Flag every negative format and qualified external rate. "
     "Domestic status and role fit determine squad priority; batting and bowling scores are not pooled.")
table(["Tier / target","Incumbent A","Action"],[
    ["P1 | Klaasen +30.48","Hetmyer -1.47; Ferreira ineligible (11 balls)",
     "First overseas No. 4-6 target. Reliable sample, limited pressure-specific lift. Rinku is the domestic fallback."],
    ["P1 spin | Varun +29.19","Bishnoi -15.13; Jadeja +1.11",
     "First spin upgrade, after batting unless pace is vacant. Preferred to Rashid: domestic, positive in both formats, stable after removal."],
    ["P1 if Archer leaves; otherwise P2 | Hazlewood +30.97","Archer +15.17; Burger ineligible (17 balls)",
     "First pace replacement; no automatic reason to replace a fit Archer. T20I rate is negative on 48 balls and no qualified external sample exists."],
    ["P2 | Rinku +25.29","Hetmyer -1.47; Ferreira ineligible",
     "Domestic batting fallback. Positive in both formats; remains tenth after removal. No qualified external sample."],
    ["P2 | Tilak +25.23","Parag -4.33; Jurel ineligible (55 balls)",
     "Preferred stable option if a top-four role opens. Positive in both formats; stays tenth. Do not force a top-four reshuffle."],
],[143,119,226],4)
text("Does the incumbent advantage survive other specifications?", "head")
table(["Target / incumbent","A margin","B margin","Remove best:<br/>A / B margins"],[
    ["Klaasen / Hetmyer",margin("Heinrich Klaasen"),margin("Heinrich Klaasen","B"),
     margin("Heinrich Klaasen","drop_A")+" / "+margin("Heinrich Klaasen","drop_B")],
    ["Varun / Bishnoi",margin("Varun Chakravarthy"),margin("Varun Chakravarthy","B"),
     margin("Varun Chakravarthy","drop_A")+" / "+margin("Varun Chakravarthy","drop_B")],
    ["Hazlewood / Archer",margin("Josh Hazlewood"),margin("Josh Hazlewood","B"),
     margin("Josh Hazlewood","drop_A")+" / "+margin("Josh Hazlewood","drop_B")],
],[167,83,83,155],4)
text("Margins are descriptive rating points, not expected runs per match. B uses an ordinary-ability prior of 240 balls for both "
     "roles, selected on 2024-25. Removal holds the incumbent and ordinary prior fixed. Conditional 95% match-bootstrap A-margin "
     "intervals: Klaasen "+interval(comparisons['Heinrich Klaasen']['A_margin_conditional_95'])+", Varun "
     +interval(comparisons['Varun Chakravarthy']['A_margin_conditional_95'])+", Hazlewood "
     +interval(comparisons['Josh Hazlewood']['A_margin_conditional_95'])+". These selected comparisons are exploratory.","note")
text("<b>Budget rule:</b> reserve money for every required role before bidding for an upgrade. Use priority tiers; no calibrated "
     "rupee ceiling can be inferred from these ratings. This policy was revised after review and is not presented as preregistered.","note")

page("The rest of the shortlist",
     "The same removal test applies to every player. Statistical ranking does not establish auction availability.")
table(["Tier / target / A rating","RR comparator A","Decision and reason"],[
    ["P3 | Brevis +34.43","Hetmyer -1.47",
     "Upside only. Best share 36%; drops to 12th. SA20 supports him, but cannot erase concentrated supplied-pack evidence."],
    ["P3 | Iyer +29.67","Parag -4.33; Jurel ineligible (55 balls)",
     "Same caution as Brevis. Best share 28%; drops to 11th; T20I -26.4 on 32 balls. Tilak is the stable top-four option."],
    ["P3 | Pooran +24.78","Hetmyer -1.47",
     "Overseas batting watchlist. Drops to 16th; external adjusted rate is positive but lift is negative."],
    ["P3 | Chapman +24.87","Hetmyer -1.47",
     "No qualifying IPL exposure; drops to 17th. Do not prioritise over the supported batting options."],
    ["P3 | Kamindu +22.72","Parag -4.33",
     "Only two IPL pressure balls; drops to 19th. Overseas top-four overlap lowers squad priority."],
    ["P3 | Tim David +20.50","Hetmyer -1.47",
     "Drops to 19th; external adjusted rate -29.04. Keep below Klaasen and Rinku."],
    ["X | Iftikhar +32.61","Hetmyer -1.47",
     "Statistical benchmark. Ineligible after best-match removal; no IPL pressure sample or verified acquisition route."],
    ["P2 | Hasaranga +27.00","Bishnoi -15.13",
     "Spin fallback behind Varun. Stable fifth after removal, but IPL value only +3.8 per 100; requires an overseas slot."],
    ["P2 | Holder +23.76","Sandeep +5.32",
     "Pace-depth fallback. Stays ninth; positive in both formats and external sample. Bowling score does not value his batting."],
    ["P3 | Rashid +33.98","Bishnoi -15.13",
     "Strong supplied-pack result, second after removal. External -8.27 and overseas cost prevent first spin priority."],
    ["P3 | Naveen +22.47","Sandeep +5.32; Burger ineligible (17 balls)",
     "Exactly 60 balls; becomes ineligible after removal. External -19.74. Do not lead the pace plan."],
    ["P3 | Hardik +20.78","Jadeja +1.11 (bowling only)",
     "Drops to 12th. Different bowling roles; batting and all-round value require a separate assessment."],
    ["P3 | Narine +18.30","Bishnoi -15.13",
     "External +68.68 supports further review, but drops to 12th. Varun has stronger removal stability and is domestic."],
    ["R | Archer +15.17","Existing RR pace role",
     "Plan retention around 198 powerplay and 102 death balls. Fifteenth after removal; retention is about coverage."],
    ["X | Shaheen +21.53","Archer +15.17",
     "Benchmark only. Ineligible after removal; no IPL pressure sample or verified acquisition route."],
],[135,111,242],3)
text("These are role comparators, not complete player valuations. Clubs verified for the 2026 season include Klaasen/SRH, "
     "Hazlewood/RCB, Varun/KKR, Iyer/PBKS, Brevis/CSK and Rashid/GT. None is assumed released or registered for 2027.","note")
text("As of 15 November 2026, Cricbuzz reports retention lists due 17 November and the auction register on 3 December "
     "(not the auction date). Confirm releases, registration, purse and overseas slots before execution. "
     +link("2026 IPL retentions","https://www.iplt20.com/news/article/tata-ipl-2026-player-retentions-announced")+"; "
     +link("RR auction additions","https://www.rajasthanroyals.com/latest-news/ipl-2026-auction-rajasthan-royals-squad-full-players-list")+"; "
     +link("Reported 2027 timeline","https://www.cricbuzz.com/cricket-news/140762/bcci-extends-ipl-retention-deadline-to-november-17-cricbuzzcom")+".","note")

page("What validation supports","A is a historical contribution measure. Predictive superiority has not been established.")
text("Same players and outcomes, including simple baselines", "head")
rows=[]
forecast = decision_audit["forecast"]
for key,label in (("zero","Zero forecast"),("ordinary_only","Ordinary ability only")):
    b,w=(forecast[role] for role in ("Batters","Bowlers"))
    bm,wm=(item['folds']['2026']['metrics'][key] for item in (b,w))
    def corr_label(metrics):
        return f"{metrics['spearman']:.3f}" if metrics['spearman'] is not None else "n/a"
    rows.append([label,f"{b['development_rmse'][key]:.2f} / {w['development_rmse'][key]:.2f}",
                 f"{bm['rmse']:.2f} / {corr_label(bm)}",f"{wm['rmse']:.2f} / {corr_label(wm)}"])
for key,label in (("current","A · Current rating"),("ordinary_prior","B · Ordinary-ability prior"),
                  ("ordinary_prior_match_cap","B + match exposure cap"),("robust_match_value","C · Cap extreme match values")):
    b,w=(prior[role]["metrics"][key] for role in ("Batters","Bowlers"))
    rows.append([label,f"{b['dev_rmse']:.2f} / {w['dev_rmse']:.2f}",
                 f"{b['holdout_rmse']:.2f} / {b['holdout_spearman']:.3f}",
                 f"{w['holdout_rmse']:.2f} / {w['holdout_spearman']:.3f}"])
table(["Experiment","2024–25 RMSE<br/>Bat / Bowl","2026 batters<br/>RMSE / rank corr.","2026 bowlers<br/>RMSE / rank corr."],
      rows,[160,98,115,115])
text("RMSE units: run equivalents per 100 pressure balls; lower is better. 2024-25 entries pool the two annual mean squared "
     "errors equally. 2026 cohorts: 14 batters and 16 bowlers. A zero forecast has no rank correlation. Ordinary ability alone "
     "has the lowest development RMSE; A is not the best forecasting model in this comparison.","note")
table(["2026 paired improvement<br/>95% interval","Batters","Bowlers"],[
    ["Zero RMSE minus A RMSE",*[interval(forecast[role]['folds']['2026']['rmse_improvement_95']['zero_minus_A']) for role in ('Batters','Bowlers')]],
    ["A RMSE minus B RMSE",*[interval(forecast[role]['folds']['2026']['rmse_improvement_95']['A_minus_B']) for role in ('Batters','Bowlers')]],
],[238,125,125],4)
text("All four intervals include zero (4,000 paired whole-match resamples, fixed forecasts/cohorts). Two-sided player-label "
     "permutation tests for A's rank correlation give p=0.156 and p=0.415 (20,000 permutations). A lower bowling "
     "rank correlation for B is not, by itself, a reason to reject B.","note")
text("<b>Why retain A?</b> A measures historical adjusted contribution. B mixes pressure evidence with ordinary ability and "
     "is used in acquisition sensitivity checks. B wins five of six reported metrics; this report does not claim A is superior. "
     "All 2026 results are retrospective diagnostics after repeated inspection.")
text("<b>Future switching rule, declared now:</b> freeze the candidate/settings before fresh data; switch the forecasting "
     "model only if its paired 95% RMSE-improvement interval is above zero against both A and zero. Report rank uncertainty "
     "rather than vetoing a model on a noisy point estimate. This rule has not been prospectively tested.","note")
text("Experiment D · Role-specific first-innings pressure","head")
rows=[]
for year,fold in experiment_d["folds"].items():
    rows.append([f"{year} · {fold['players']} bowlers",*
                 [f"{fold['variants'][v]['rmse']:.2f} / {fold['variants'][v]['spearman']:.3f}" for v in ("A","D1","D2")]])
table(["Year and cohort","A · Collapse rule","D1 · 9 RPO","D2 · Format/phase quartile"],rows,[142,106,107,133])
text("Entries are RMSE / Spearman. Both D variants were worse in both historical folds. Training pressure definitions differed; "
     "evaluation always used the same players and their held-out adjusted contribution on Model A-defined pressure deliveries. "
     "Predictions were not identical.","note")
text("Limits: fixed wicket values; uneven opportunities; resampling holds fitted baselines and eligibility fixed. "
     "The future-outcome perturbation audit left earlier scores and frozen expectations unchanged. Sources: supplied brief/CSVs, "
     "recreated evidence, chronological and external validation. "
     +link("Competition listing","https://unstop.com/hackathons/crp-superr-selector-season-2-help-shape-rajasthan-royals-ipl-2027-auction-strategy-rajasthan-royals-1792758")+".","note")

if args.external_validation:
    external_panel(args.external_validation)

def footer(canvas, doc):
    canvas.setStrokeColor(grid)
    canvas.line(48,42,A4[0]-48,42)
    canvas.setFont("Helvetica",8)
    canvas.setFillColor(muted)
    canvas.drawString(48,29,"SupeRR Selector  /  Scouting dossier")
    canvas.drawRightString(A4[0]-48,29,str(doc.page))

path=args.output
path.parent.mkdir(parents=True,exist_ok=True)
doc=SimpleDocTemplate(str(path),pagesize=A4,leftMargin=48,rightMargin=48,topMargin=42,bottomMargin=53,
                      title="SupeRR Selector Round 1 | Rajasthan Royals scouting dossier")
doc.build(story,onFirstPage=footer,onLaterPages=footer)


