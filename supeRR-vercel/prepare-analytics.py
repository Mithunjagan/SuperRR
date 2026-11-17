"""Attach reviewed player-match aggregates for the dashboard's model explorer."""
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
snapshot_path = ROOT / "supeRR-dashboard/src/data.json"
snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
rows = []
for role, filename in [("Batters", "batters_match_evidence.csv"), ("Bowlers", "bowlers_match_evidence.csv")]:
    shortlist = {p["name"]: p for p in snapshot["queries"]["shortlist"]["rows"] if p["role"] == role}
    with (ROOT / "output/final_recheck" / filename).open(encoding="utf-8-sig", newline="") as source:
        for match in csv.DictReader(source):
            if match["name"] in shortlist:
                rows.append({"name": match["name"], "role": role, "matchId": int(match["match_id"]),
                             "value": float(match["value"]), "balls": int(match["balls"]), "lift": float(match["lift"])})
    for name, player in shortlist.items():
        games = [r for r in rows if r["role"] == role and r["name"] == name]
        balls, value = sum(g["balls"] for g in games), sum(g["value"] for g in games)
        assert balls == player["balls"]
        assert sum(g["balls"] > 0 for g in games) == player["matches"]
        deletion = min(100 * (value - g["value"]) / (balls - g["balls"] + 60) for g in games)
        assert abs(deletion - player["score"]) < 0.000001, (name, deletion, player["score"])

snapshot["buildStatus"] = "updating"
for query in snapshot["queries"].values():
    source = query.get("source", {})
    if "title" in source:
        source.setdefault("label", source.pop("title"))
snapshot["queries"]["matchEvidence"] = {
    "rows": rows,
    "source": {
        "provider": "SupeRR Round 1 analysis", "label": "Reviewed shortlist player-match contributions",
        "files": ["output/final_recheck/batters_match_evidence.csv", "output/final_recheck/bowlers_match_evidence.csv",
                  "output/final_recheck/final_rankings.json", "audit_match_reliability.py"],
        "grain": "One qualifying player-match contribution, for the final ten batters and ten bowlers",
        "metricDefinitions": [
            {"label": "Sensitivity rating", "definition": "Minimum over match deletions of 100 times remaining adjusted value divided by remaining balls plus the selected shrinkage. At 60 added balls this reproduces the official final rating. Eligibility and contributions stay fixed. Other strengths are exploratory diagnostics, not a new submission order.",
             "componentIds": ["shrinkage-curves"], "formula": "min_match(100 * (totalValue - matchValue) / (totalBalls - matchBalls + shrinkage))"},
            {"label": "Match contribution", "definition": "Adjusted runs contributed in one observed match. Values include zero-exposure extras-only bowling records; only positive-exposure records count as matches. Records are ordered by supplied match ID, not by date.", "componentIds": ["match-contributions"]}
        ],
        "evidenceFlow": [{"title": "Reproduce analytics inputs", "detail": "Run python supeRR-vercel/prepare-analytics.py. Select the official ten in each role from the existing reviewed shortlist, retain all their player-match aggregates, and assert ball totals, positive-exposure match counts, and every 60-ball deletion rating against the reviewed shortlist. No delivery-level data is added."}]
    },
    "methods": [{"language": "text", "code": "Source aggregates are prepared by supeRR-vercel/prepare-analytics.py. Interactive calculations are in src/content/dashboard/pressure-analytics.mjs. Preserve frozen eligibility and the official 60-ball ranking; a different shrinkage is a sensitivity scenario. Per-match bars show supplied adjusted value, ordered by match ID; they are not a chronological time series."}]
}
snapshot_path.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
print(f"Verified and attached {len(rows)} match aggregates for 20 shortlisted players.")
