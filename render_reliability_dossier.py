"""Render the Round 1 submission from the match-reliability audit."""

import argparse
import json
from html import escape
from pathlib import Path

from reportlab.lib.colors import HexColor, white
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


INK = HexColor("#182538")
MUTED = HexColor("#4D5D72")
PINK = HexColor("#A81F60")
PALE = HexColor("#F1F5F9")
GRID = HexColor("#D8E1EB")
WIDTH = A4[0] - 100
ROLES = ("Batters", "Bowlers")

FIT = {
    "Heinrich Klaasen": "First overseas finishing target.",
    "Reeza Hendricks": "Top-order depth. T20I evidence only.",
    "Shubman Gill": "Domestic top-order option if a slot opens.",
    "Shreyas Iyer": "Domestic chase option if a batting slot opens.",
    "Mark Chapman": "Overseas batting depth. T20I evidence only.",
    "Suryakumar Yadav": "High-output batting benchmark. Lift is negative.",
    "Nicholas Pooran": "Overseas finishing alternative.",
    "Namboori Tilak Varma": "Domestic option if RR reopens a top-four role.",
    "Virat Kohli": "Domestic top-order benchmark.",
    "Jos Buttler": "Overseas top-order alternative if the role opens.",
    "Akeal Hosein": "Overseas spin option. IPL sample is 24 balls.",
    "Jasprit Bumrah": "Pace benchmark and conditional target.",
    "Sunil Narine": "Overseas spin option with public-league support.",
    "Varun Chakravarthy": "First domestic spin target.",
    "Jason Holder": "Pace-depth option. Batting is outside this score.",
    "Mohammad Nawaz": "Spin benchmark. T20I evidence only.",
    "Rashid Khan": "Spin benchmark. External pressure rate is negative.",
    "Naveen ul Haq": "Pace watchlist. External pressure rate is negative.",
    "Mitchell Santner": "Overseas spin-depth alternative.",
    "Jofra Archer": "Retain if feasible to cover new-ball and death overs.",
}


def make_styles():
    sizes = {
        "tag": (9, 12, PINK, True, 9),
        "title": (28, 32, INK, True, 9),
        "intro": (12, 16, MUTED, False, 16),
        "head": (13, 17, INK, True, 5),
        "body": (10.4, 15, INK, False, 10),
        "note": (9, 13, MUTED, False, 7),
        "cell": (9, 12, INK, False, 0),
        "number": (9, 12, INK, True, 0),
        "th": (8.5, 11, white, True, 0),
    }
    return {key: ParagraphStyle(
        key, fontName="Helvetica-Bold" if bold else "Helvetica", fontSize=size,
        leading=leading, textColor=color, spaceAfter=space,
        spaceBefore=9 if key == "head" else 0,
        alignment=TA_RIGHT if key == "number" else 0,
    ) for key, (size, leading, color, bold, space) in sizes.items()}


def signed(number):
    return f"{number:+.2f}"


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def footer(canvas, doc):
    canvas.setStrokeColor(GRID)
    canvas.line(50, 42, A4[0] - 50, 42)
    canvas.setFillColor(MUTED)
    canvas.setFont("Helvetica", 8)
    canvas.drawString(50, 28, "SupeRR Selector  /  Round 1 methodology and scouting report")
    canvas.drawRightString(A4[0] - 50, 28, str(doc.page))


def render(audit, destination):
    styles = make_styles()
    story = []
    models = {role: audit[role]["proposed"] for role in ROLES}
    final = {role: model["ranking"][:10] for role, model in models.items()}
    by_name = {role: {r["name"]: r for r in model["ranking"]} for role, model in models.items()}
    prior = {role: {r["name"]: r for r in audit[role]["original"]} for role in ROLES}

    def paragraph(content, style="body"):
        story.append(Paragraph(content, styles[style]))

    def page(title, intro):
        if story:
            story.append(PageBreak())
        paragraph("SUPERR SELECTOR  /  RAJASTHAN ROYALS  /  ROUND 1", "tag")
        paragraph(title, "title")
        paragraph(intro, "intro")

    def section(title, content):
        paragraph(title, "head")
        paragraph(content)

    def table(headers, values, weights, numeric=(), padding=6):
        scale = WIDTH / sum(weights)
        result = [[Paragraph(h, styles["th"]) for h in headers]]
        for row in values:
            result.append([Paragraph(escape(str(value)), styles["number" if i in numeric else "cell"])
                           for i, value in enumerate(row)])
        block = Table(result, colWidths=[w * scale for w in weights], repeatRows=1, hAlign="LEFT")
        block.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), INK),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [white, PALE]),
            ("LINEBELOW", (0, -1), (-1, -1), 0.5, GRID),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), padding),
            ("BOTTOMPADDING", (0, 0), (-1, -1), padding),
        ]))
        story.append(block)
        story.append(Spacer(1, 10))

    def score_of(role, name):
        return by_name[role][name]["score"]

    page("Rajasthan Royals scouting dossier",
         "Pressure reliability and auction fit  /  16 November 2026")
    section("Prioritise Klaasen and Varun",
            f"Klaasen leads the batting list at <b>{score_of('Batters', 'Heinrich Klaasen'):.2f}</b> with "
            "310 qualifying balls across 32 matches. He is the first overseas finishing target. "
            f"Varun is fourth among bowlers at <b>{score_of('Bowlers', 'Varun Chakravarthy'):.2f}</b>, "
            "leads the domestic spin options in the final list and uses a domestic slot.")
    table(["Order", "RR decision", "Evidence"], [
        ["1", "Overseas finishing", "Klaasen is first overall and second in the chase-only check."],
        ["2", "Domestic spin upgrade", "Varun is fourth overall, eighth in chases and ahead of Bishnoi on this rating."],
        ["Conditional first", "Replace Archer's role if he leaves", "Cover the powerplay and death allocation before funding discretionary upgrades."],
    ], [85, 156, 247], padding=8)
    section("The rankings discount dependence on one match",
            "Every ranked player retains at least 60 qualifying balls across eight matches after any one match "
            "is removed. The final rating is the lowest score across those removals. Earlier competitive chases "
            "now count alongside the original late chases and first-innings collapses.")
    section("Pressure evidence for the auction desk",
            "Akeal Hosein leads the bowling list on this historical score. Bumrah and Narine follow, and both "
            "also make the chase-only top four. Confirm player availability and phase fit before making a bid. "
            "Pages 3 and 4 give the exact Round 1 dropdown order.")

    page("How the rating works",
         "Deliveries are adjusted for match context and opponent, then aggregated at match level.")
    section("Pressure situations",
            f"The supplied IPL and T20I pack contributes 184,476 regulation delivery events in 771 screened matches "
            f"from 2022 to 2026. The expanded rule flags {audit['pressure_events']:,} events before role and player "
            f"filters, adding {audit['added_chase_events']:,} to the original 14,381. Super Overs and revised matches are excluded.")
    table(["Situation", "Pre-delivery condition"], [
        ["First-innings collapse", "At least three wickets down before 60 legal balls."],
        ["Late chase", "1-30 legal balls left, 8-16 required runs per over, at least two wickets in hand."],
        ["Earlier competitive chase", "31-60 legal balls left, 9.5-16 required runs per over, at least two wickets in hand."],
    ], [150, 338])
    paragraph("The earlier chase window captures sustained scoring pressure. The rate ceiling and wickets-in-hand rule "
              "keep the focus on chases that still have a plausible route to the target.", "note")
    section("Adjusted contribution and the ordinary baseline",
            "Batting value is runs off the bat minus dismissal cost. Bowling value is credited wicket value minus "
            "charged runs, including wides and no-balls. Wickets carry 8, 6 and 4 run equivalents in the powerplay, "
            "middle and death. Run-outs earn no bowling credit. Bowling exposure counts legal balls. Batting exposure "
            "excludes wides and off-delivery penalties. Expected contribution uses earlier dates within "
            "format, innings and phase, with adjustments for balls left, wickets lost, scoring rate and opponent. "
            "Ordinary-play lift compares this residual with the player's own earlier adjusted ordinary rate.")
    section("One-match removal score",
            "Group adjusted values and exposure balls by player and match. Remove each match in turn and recalculate "
            "<b>100 x remaining adjusted value / (remaining balls + 60)</b>. The lowest result is the final score. "
            "Players need 120 prior ordinary balls per event and must retain at least 60 pressure balls in eight matches "
            "with positive ball exposure under every removal. Scores descend within each role. Ties use original "
            "pressure balls, then supplied player ID.")
    paragraph("State buckets use six balls within 30 remaining and 12 otherwise. Wicket boundaries are 1, 2, 3, 4, 6 and 9. "
              "Rate bins are two runs per over up to 30. Phase priors use 100 virtual balls at +1 for batting or -1 for bowling. "
              "The state tiers borrow 100 and 60 balls, and opponent and ordinary-player estimates borrow 60 toward zero. "
              "The expanded flag is also used when estimating ordinary history. Screening reconciles innings totals and results.", "note")

    for role in ROLES:
        page(f"Top 10 {role.lower()}",
             f"Submit in the order shown. {models[role]['eligible']} players in this role met the one-match removal eligibility rule.")
        lines = []
        for r in final[role]:
            position = r.get("batting_position")
            sample = f"{r['ipl_balls']}/{r['balls']}"
            detail = f"No. {position:g}" if position is not None else r["busiest_phase"]
            lines.append([r["rank"], r["name"], f"{r['score']:.2f}", sample,
                          f"{r['positive_matches']}/{r['matches']}", signed(r["lift_per100"]), detail, FIT[r["name"]]])
        table(["#", "Player", "Score", "IPL / all<br/>balls", "Positive<br/>matches", "Lift /<br/>100",
               "Observed<br/>role", "RR use"], lines, [32, 103, 41, 46, 48, 40, 55, 123], (0, 2, 3, 4, 5), padding=6)
        paragraph("Score is the worst leave-one-match-out rating. Lift per 100 is the unshrunk difference versus that player's "
                  "own earlier ordinary play. Observed batting role is the median batting position across qualifying innings. "
                  "Observed bowling role is the phase with the most qualifying legal deliveries.", "note")
        if role == "Batters":
            section("Why Klaasen leads",
                    "Klaasen has 280 IPL balls in the final sample and ranks second when only chases count. SKY ranks "
                    "sixth overall and third in the chase check. His small negative lift reflects the strength of his ordinary baseline.")
        else:
            section("Read the first three together",
                    "Hosein and Bumrah are separated by only 0.44 rating points. Bumrah has 113 qualifying IPL balls "
                    "versus Hosein's 24 and leads the chase-only check. Narine brings 239 qualifying IPL balls and ranks fourth in chases.")

    page("What changed and what held up",
         "Retrospective checks on aggregation, match context and transfer to 2026.")
    section("How the ranking responds",
            "An 8,000-draw player-level whole-match bootstrap on the original pressure definition ranks by the "
            "25th percentile. It moves Klaasen from third to first and Brevis from first to third, while Iftikhar "
            "remains second. It retains 9 of 10 original batters and all 10 original bowlers. The final rule directly "
            "tests the effect of removing one match and expands coverage to earlier competitive chases.")
    comparisons = []
    subjects = [
        ("Batters", "Heinrich Klaasen"), ("Batters", "Dewald Brevis"), ("Batters", "Iftikhar Ahmed"),
        ("Batters", "Suryakumar Yadav"), ("Bowlers", "Jasprit Bumrah"), ("Bowlers", "Sunil Narine"),
        ("Bowlers", "Hardik Pandya"),
    ]
    for role, name in subjects:
        old, new = prior[role][name], by_name[role][name]
        comparisons.append([name, old["rank_a"], old["rank_reliability"], new["rank"]])
    table(["Player", "Original A", "Original window<br/>bootstrap", "Final rank"], comparisons,
          [150, 95, 122, 121], (1, 2, 3), padding=4)
    paragraph("The original pooled top tens shared 3 of 10 names per role with a broader chase-only stress test "
              "(last 60 balls, required rate at least 9.5, with the original per-delivery scoring and eligibility rules). "
              f"The final mixed-window lists share {models['Batters']['chase_overlap']} batting and "
              f"{models['Bowlers']['chase_overlap']} bowling names with their own competitive chase-only rankings.", "note")
    forward = []
    for role in ROLES:
        check = models[role]["forward"]
        forward.append([role, check["players"], f"{check['pooled']['rmse']:.2f} / {check['reliability']['rmse']:.2f}",
                        f"{check['pooled']['spearman']:+.3f} / {check['reliability']['spearman']:+.3f}"])
    table(["2026 diagnostic", "Players", "RMSE<br/>pooled / final", "Spearman<br/>pooled / final"],
          forward, [140, 62, 143, 143], (1, 2, 3), padding=4)
    paragraph("Training uses matches before 2026. The evaluation compares future adjusted value on the same players "
              "within each role, with baselines frozen at the split. These retrospective diagnostics show mixed "
              "forecast results. The final score measures historical resilience to one-match removal.", "note")

    page("Auction decisions and limits",
         "A ranking measures pressure performance. Bidding also needs role coverage, price and availability.")
    comparisons = [
        ("Finishing", "Batters", "Heinrich Klaasen", "Shimron Hetmyer"),
        ("Domestic spin", "Bowlers", "Varun Chakravarthy", "Ravi Bishnoi"),
        ("Pace cover", "Bowlers", "Josh Hazlewood", "Jofra Archer"),
    ]
    rows = []
    for role, group, target, incumbent in comparisons:
        rows.append([role, target, incumbent, signed(score_of(group, target)),
                     signed(score_of(group, incumbent)), signed(score_of(group, target) - score_of(group, incumbent))])
    table(["Role", "Target", "Incumbent", "Target<br/>rating", "Incumbent<br/>rating", "Margin"], rows,
          [80, 105, 103, 60, 80, 60], (3, 4, 5))
    section("Finishing and spin",
            "Klaasen has the strongest finishing case among the named targets. Ferreira has no eligible final-rating "
            "comparison. Varun improves the pressure score over Bishnoi. RR already used Jadeja, Punja and Bishnoi for "
            "462 middle-over balls across 15 screened 2026 matches, so this is an upgrade decision.")
    section("Plan pace coverage around Archer",
            "Archer delivered 198 powerplay and 102 death balls for RR in the screened 2026 sample. His departure would "
            "move those two phases to the front of the budget. Hazlewood is a conditional comparison for that role. "
            "Archer leads him on the final rating, so the score gives no reason to replace a retained Archer.")
    section("Independent league evidence",
            "A separate Cricsheet check used the original pressure definition on 610 BBL, PSL, SA20 and CPL matches. "
            "It found +30.29 adjusted runs per 100 for Klaasen (96 balls), +68.68 for Narine (64, including 58 in the CPL), "
            "and -8.27 for Rashid (83). These rates give context to individual picks and were kept out of the final score.")
    paragraph("All role margins are descriptive. Check releases, registration, purse and available overseas slots. "
              "Player rank alone provides no rupee valuation.", "note")
    paragraph('Sources: Rajasthan Royals Round 1 problem statement and supplied CSVs. '
              '<link href="https://cricsheet.org/downloads/" color="#245C88">Cricsheet public match data</link>. '
              '<link href="https://www.rajasthanroyals.com/rr-players" color="#245C88">Rajasthan Royals squad</link>.', "note")

    page("Original Model A reference",
         "Earlier pooled rankings on the original pressure definition, retained for comparison.")
    earlier = {role: sorted(audit[role]["original"], key=lambda r: r["rank_a"])[:10] for role in ROLES}
    table(["Rank", "Original batter", "A score", "Original bowler", "A score"], [
        [i + 1, batter["name"], f"{batter['model_a']:.2f}", bowler["name"], f"{bowler['model_a']:.2f}"]
        for i, (batter, bowler) in enumerate(zip(earlier["Batters"], earlier["Bowlers"]))
    ], [38, 161, 61, 167, 61], (0, 2, 4))
    section("Brevis illustrates the change",
            "The original score of 34.43 comes from +57.15 adjusted run equivalents in 106 balls, shrunk by 60 virtual "
            "balls. First-innings collapses contributed +69.35 and qualifying chases -12.20. Removing one match dropped "
            "him to 12th in the original ranking. He ranks 31st on the final score.")
    section("Reproduce the report",
            "Run <b>python audit_match_reliability.py --output ranking.json</b> with the supplied Data Pack in the "
            "project root, then <b>python render_reliability_dossier.py ranking.json output.pdf</b>. The bootstrap diagnostic "
            "uses seed 161126 mixed with supplied player ID. It holds scored deliveries and eligibility fixed and samples "
            "the same number of whole matches as each player originally had.")

    destination.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(str(destination), pagesize=A4, leftMargin=50, rightMargin=50,
                            topMargin=49, bottomMargin=59, title="SupeRR Selector | Round 1 reliability dossier")
    doc.build(story, onFirstPage=footer, onLaterPages=footer)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("audit", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    render(load_json(args.audit), args.output)
