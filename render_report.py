"""Render the revised PDF from the verified ranking JSON."""
import json
from html import escape
from pathlib import Path

from reportlab.lib.colors import HexColor, white
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Table, TableStyle

output = Path("output")
data = json.loads((output / "revised_rankings.json").read_text(encoding="utf-8"))
path = output / "pdf" / "SupeRR Round 1 Methodology - Revised.pdf"
ink = HexColor("#15253C")
secondary = HexColor("#425269")
accent = HexColor("#A01757")
pale = HexColor("#F0F4F8")
style = {
    "tag": ParagraphStyle("tag", fontName="Helvetica-Bold", fontSize=9, textColor=accent, leading=13, spaceAfter=9),
    "title": ParagraphStyle("title", fontName="Helvetica-Bold", fontSize=29, leading=33, textColor=ink, spaceAfter=9),
    "intro": ParagraphStyle("intro", fontSize=11, leading=16, textColor=secondary, spaceAfter=12),
    "heading": ParagraphStyle("heading", fontName="Helvetica-Bold", fontSize=13, leading=17, textColor=ink,
                              spaceBefore=11, spaceAfter=4),
    "body": ParagraphStyle("body", fontSize=10.2, leading=14.4, textColor=ink, spaceAfter=7),
    "note": ParagraphStyle("note", fontSize=9, leading=12.6, textColor=secondary, spaceBefore=7, spaceAfter=6),
    "cell": ParagraphStyle("cell", fontSize=8.8, leading=11, textColor=ink),
    "header": ParagraphStyle("header", fontName="Helvetica-Bold", fontSize=8.2, leading=10, textColor=white),
}
story = []

def text(value, kind="body"):
    story.append(Paragraph(str(value), style[kind]))

def section(title, body):
    text(title, "heading")
    text(body)

def page(title, intro):
    text("RAJASTHAN ROYALS   /   SUPERR SELECTOR SEASON 2   /   ROUND 1", "tag")
    text(title, "title")
    text(intro, "intro")

def table(head, rows, widths, heights=None):
    grid = [[Paragraph(cell, style["header"]) for cell in head]]
    grid += [[Paragraph(escape(str(cell)), style["cell"]) for cell in row] for row in rows]
    box = Table(grid, colWidths=widths, rowHeights=heights, repeatRows=1, hAlign="LEFT")
    box.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), ink),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [white, pale]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(box)

page("Who delivers under pressure?", "Batting and bowling rankings adjusted for match state and individual opponent strength.")
section("Match sample",
        "The analysis uses 184,476 regulation delivery events from 771 matches (352 IPL, 419 T20I), spanning 2022 to 2026. "
        "Of 883 match records, 30 were emerging-team events, 16 had no delivery records, 38 had revision indicators or DLS results, "
        "15 lacked a complete result or both innings, and 13 failed innings or score reconciliation. These exclusion counts are sequential. "
        "Super Over deliveries are excluded.")
section("Pressure before the delivery",
        "Late chase: 1 to 30 legal balls left, 8 to 16 required runs per over, and at least two wickets in hand. "
        "Required rate equals six times runs needed divided by legal balls left. First innings: at least three wickets "
        "already lost before 60 legal balls have been used. Together these rules identify 14,381 delivery events before role and player eligibility filters.")
section("Actual value and expected value",
        "A batter earns runs off the bat minus dismissal cost. A bowler earns credited wicket value minus runs charged, including wides and "
        "no-balls. The wicket value is 8, 6 or 4 run equivalents in overs 1 to 6, 7 to 15 or 16 to 20. Batting exposure omits wides and off-delivery "
        "penalties. Bowling exposure counts legal balls, while illegal deliveries still contribute charged runs and eligible wickets. "
        "Run-outs earn no bowling wicket credit. The pack's one-run primary extra marked “other” is treated as a no-ball.")
text("We fit separate batting and bowling expectations using only earlier match dates. Within format, innings and phase, we smooth results "
     "first by balls remaining and wickets lost, then by required run rate in chases or current run rate in first innings. We use 6-ball bins "
     "in the last 30 balls, 12-ball bins earlier, wicket cut points at 1, 2, 3, 4, 6 and 9 lost, and 2-run-per-over rate bands capped at 30. "
     "The phase reference starts with 100 virtual balls at +1 for batting and -1 for bowling. The two state levels borrow 100 and 60 balls "
     "from their parent estimates. The individual opponent adjustment uses the opposing bowler or batter's earlier ordinary-play residual "
     "in the same format, innings and phase, shrunk toward zero with 60 virtual balls.")
section("Rank and lift",
        "<b>Rating = 100 × total (actual value minus expected value) ÷ (eligible pressure balls + 60).</b> A ball is eligible once the "
        "player has 120 prior ordinary balls. A player needs 60 eligible pressure balls across eight matches. Lift compares pressure "
        "residuals with the player's own earlier ordinary residual rate, smoothed with 60 virtual balls. Lift is reported alongside the rating.")
text("Sources include the supplied SupeRR Round 1 brief and the match, competition and delivery CSVs. "
     "The calculation uses dated delivery records and player IDs.", "note")

for role in ("Batters", "Bowlers"):
    story.append(PageBreak())
    d = data[role]
    page(f"Top 10 {role.lower()}", f"{d['eligible']} eligible players. {d['original_overlap']} of the original ten appear in this list.")
    rows = []
    for x in d["top"]:
        rows.append([x["rank"], x["name"], f"{x['rating']:.2f}", f"{x['per100']:+.1f}", f"{x['lift_per100']:+.1f}",
                     x["balls"], x["matches"], f"{x['p_top10']:.0%}",
                     f"{x['rank_low']}-{x['rank_high']}", int(x["original_rank"]) if x["original_rank"] is not None else "—"])
    table(["Rank", "Player", "Rating", "Value<br/>per 100", "Lift<br/>per 100", "Balls", "Games", "Top 10<br/>share",
           "Rank<br/>range", "Prior<br/>rank"], rows, [37, 106, 42, 48, 46, 33, 44, 49, 47, 36], [31] + [23] * 10)
    text("Value and lift per 100 balls are adjusted run equivalents before final shrinkage. Top-ten frequency and 95% rank ranges come from 1,000 whole-match resamples with fitted expectations and eligibility held fixed. "
         "The ranges describe resampling uncertainty under this model and depend on the observed matches.", "note")
    rows = []
    for x in d["top"]:
        rank = str(int(x["drop_best_rank"])) if x["drop_best_rank"] is not None else "Below threshold"
        rows.append([x["name"], f"{x['best_positive_share']:.0%}", f"{x['drop_best_rating']:.2f}", int(x["drop_best_balls"]), rank])
    text("Removing each player's best match", "heading")
    table(["Player", "Share of positive<br/>value from best match", "Rating after<br/>removal", "Balls left", "Rank after<br/>removal"],
          rows, [132, 110, 90, 72, 86])
    text("The best match is the one with the largest positive adjusted value. Other players' scores and the fitted expectations stay fixed.",
         "note")

story.append(PageBreak())
page("Validation and sensitivity", "The revised rating improves the bowling comparison on the 2026 holdout. The original batting rating has the stronger holdout correlation.")
bat, bowl = data["Batters"], data["Bowlers"]
table(["2026 holdout", "Batters", "Bowlers"],
      [[label, bat["holdout"][key], bowl["holdout"][key]] for label, key in (
          ("Players meeting thresholds in both periods", "n"),
          ("Revised rating vs 2026 performance", "new"),
          ("Original rating vs 2026 performance", "original"),
          ("Ordinary ability vs 2026 performance", "ordinary"))], [300, 95, 95])
text("Spearman rank correlations use a single common player pool per role. Rankings use 2022 to 2025 performances. Expectations and ordinary baselines "
     "are frozen before 2026 and the 2026 target is observed revised adjusted value per 100 pressure balls. Holdout eligibility requires at least "
     "12 balls in three matches. With 14 batters and 16 bowlers, these comparisons do not establish the exact future order.", "note")
text("Sensitivity of the pooled top ten", "heading")
table(["Change", "Batters retained", "Bowlers retained"],
      [["Alternate chase rule: 24 balls, 8 to 17 RPO", bat["window_overlap"], bowl["window_overlap"]]] +
      [[label, bat["sensitivity"][key]["overlap"], bowl["sensitivity"][key]["overlap"]]
       for label, key in [("Flat wicket value: 6, 6, 6", "flat"), ("Half wicket values", "half"),
                          ("1.5 times wicket values", "higher")]] +
      [[f"Only {fmt} pressure balls", d1["overlap"], d2["overlap"]]
       for fmt in ["IPL", "T20I"] for d1,d2 in [(bat["split"][fmt], bowl["split"][fmt])]], [300, 95, 95])
text("All counts are overlaps with the pooled revised top ten. Format splits keep the same minimum ball and match counts within each format "
     "and pool prior player experience. IPL leaders are Shreyas Iyer and Josh Hazlewood. T20I leaders are Iftikhar Ahmed and Rashid Khan.", "note")
section("What to take from the rankings",
        f"The 120-ball history rule removes {bat['cold_lost']:,} of {bat['cold_total']:,} batting pressure balls and "
        f"{bowl['cold_lost']:,} of {bowl['cold_total']:,} bowling pressure balls. The typical most-specific state has "
        f"{bat['fine_state_median']:.0f} prior batting balls or {bowl['fine_state_median']:.0f} prior bowling balls, with "
        f"{bat['fine_state_empty_pct']:.1%} and {bowl['fine_state_empty_pct']:.1%} of included events, respectively, having no prior balls at that level. "
        "Smoothing limits the effect of sparse state groups. The rankings measure historical performance in these scenarios. "
        "They remain sensitive to opportunity, wicket values and context, and the bootstrap does not refit baselines or player eligibility.")
story.append(PageBreak())
page("Rajasthan Royals auction recommendation",
     "Prioritize a No. 3–4 batter who can rebuild after early wickets, a No. 4–6 batter who can accelerate, and a bowler for the phase where the squad needs coverage.")
text("Priority scouting shortlist", "heading")
table(["Player", "Potential Royals role", "Evidence from the pressure model"], [
    ["Shreyas Iyer", "No. 3–4 batter for early-wicket recovery.",
     "No. 1 IPL-only batter and No. 4 pooled. His score falls to No. 11 when his best match is removed."],
    ["Heinrich Klaasen", "No. 4–6 batter to accelerate after a rebuild or finish a chase.",
     "No. 2 IPL-only batter. Positive adjusted value in 18 of 23 pressure matches. Stays in the pooled top four without his best match."],
    ["Josh Hazlewood", "New-ball seamer who can return at the death.",
     "No. 1 IPL-only bowler and No. 2 pooled. Bowled in both phases in the screened data. Remains eighth without his best match."],
    ["Rashid Khan", "Middle-overs leg-spinner to take wickets and slow scoring.",
     "No. 1 pooled and No. 6 in IPL alone. Positive in 31 of 44 pressure matches and second without his best match."],
], [96, 153, 241])
section("Alternatives by role",
        "<b>Varun Chakravarthy</b> is the alternative for middle-overs spin. He ranks second in IPL and third in T20I. "
        "<b>Dewald Brevis</b> is an option at No. 4–5 if the priority is middle-order acceleration. He leads the pooled batting list, "
        "with 106 pressure balls across 12 matches, and drops to 12th when his best match is removed.")
section("Where the evidence is thin",
        "<b>Iftikhar Ahmed</b> ranks second among batters, but his 62 pressure balls fall to 48 without his best match, below eligibility. "
        "<b>Naveen ul Haq</b> and <b>Shaheen Afridi</b> qualify on 60 and 66 balls and also fall below eligibility without their best matches. "
        "Treat these signals as leads for further scouting.")
text("These are role-fit recommendations based on the supplied matches. Auction availability, squad slots and price would need to be confirmed before bidding.",
     "note")


def footer(canvas, doc):
    canvas.setStrokeColor(pale)
    canvas.line(48, 42, A4[0] - 48, 42)
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(secondary)
    canvas.drawString(48, 29, "SupeRR Selector  /  Round 1 methodology")
    canvas.drawRightString(A4[0] - 48, 29, str(doc.page))

path.parent.mkdir(parents=True, exist_ok=True)
doc = SimpleDocTemplate(str(path), pagesize=A4, leftMargin=48, rightMargin=48, topMargin=42, bottomMargin=52,
                        title="SupeRR Selector Round 1 | Revised Methodology")
doc.build(story, onFirstPage=footer, onLaterPages=footer)






