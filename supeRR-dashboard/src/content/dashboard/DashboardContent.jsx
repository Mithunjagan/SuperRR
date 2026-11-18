import React, { useEffect, useLayoutEffect, useRef, useState } from "react";
import { DataComponent, useDataApp } from "../../data-app-public.jsx";
import "./pressure.css";
import "./experience.css";
import Analyst from "./Analyst.jsx";
import AnalyticsLab from "./AnalyticsLab.jsx";
import Picker from "./Picker.jsx";

const number = new Intl.NumberFormat("en-IN");
const fmt = n => Number(n).toFixed(2);
const signed = n => (n >= 0 ? "+" : "−") + fmt(Math.abs(n));
const pct = n => (n * 100).toFixed(1) + "%";
const roles = ["Batters", "Bowlers"];
const metrics = [
  ["score", "Final rating", "Adjusted runs / 100 balls"],
  ["boot_q0.25", "Bootstrap Q25", "Adjusted runs / 100 balls"],
  ["ipl_balls", "IPL balls", "Qualifying IPL balls"]
];
const nav = [["top","Overview"],["analytics","Analytics"],["rankings","Players"],["comparison","The duel"],["auction","Auction"],["methods","Method"],["analyst","Q&A"]];
const windows = [
  ["Early collapse","First innings","0–59","legal balls already bowled","At least 3 wickets lost"],
  ["Mid-chase","Second innings","31–60","legal balls remaining","9.5–16 required runs per over"],
  ["Late chase","Second innings","1–30","legal balls remaining","8–16 required runs per over"]
];
const appearanceKey = "superrr-viewer-appearance";
const appearances = [
  { value: "system", label: "System theme" },
  { value: "light", label: "Light theme" },
  { value: "dark", label: "Dark theme" },
];

function readAppearance() {
  try {
    const saved = localStorage.getItem(appearanceKey);
    if (appearances.some(option => option.value === saved)) return saved;
  } catch {
    // Appearance still works if the browser blocks storage.
  }
  return "system";
}

function Mark({ className = "" }) {
  return <span className={"rr-mark " + className} aria-hidden="true"><i/><i/><i/></span>;
}

function Evidence({ id, query, title, rows, children, className = "", headerControls }) {
  return <DataComponent id={id} queryId={query} title={title} kind="custom" variant="plain" showHeading={false} sourceRows={rows}
    className={className} headerControls={headerControls}>{children && <div data-reviewed-rows>{children}</div>}</DataComponent>;
}

function Heading({ index, title, detail }) {
  return <header className="rr-heading"><div className="rr-kicker"><span/> {index}</div>
    <h2>{title}</h2>{detail && <p>{detail}</p>}</header>;
}

function Choices({ options, value, onChange, label }) {
  return <div className="rr-choices" role="group" aria-label={label}>
    {options.map(([id, text]) => <button type="button" key={id} aria-pressed={value === id} onClick={() => onChange(id)}>{text}</button>)}
  </div>;
}

function Split({ label, left, right, total, labels }) {
  return <div className="rr-split"><strong>{label}</strong>
    <div className="rr-split-track" aria-hidden="true"><span style={{ width: left / total * 100 + "%" }} /></div>
    <div className="rr-split-label"><span><i/> {labels[0]} · {left}</span><span><i/> {labels[1]} · {right}</span></div>
  </div>;
}

function PlayerCard({ player }) {
  const low = player["boot_q0.025"], high = player["boot_q0.975"];
  const point = value => (value-low)/(high-low)*100;
  return <article className="rr-player">
    <div className="rr-player-head">
      <div><div className="rr-kicker">PLAYER FILE <b> / </b> #{String(player.final_rank).padStart(2,"0")}</div>
        <h3>{player.name}</h3><p>{player.fit}</p></div>
      <span className="rr-monogram" aria-hidden="true">{player.name.split(" ").map(word => word[0]).slice(0,2).join("")}</span>
    </div>
    <div className="rr-tiles">
      <div><small>Final rating</small><strong>{fmt(player.score)}</strong></div>
      <div><small>Pressure balls</small><strong>{player.balls}</strong></div>
      <div><small>Positive matches</small><strong>{player.positive_matches}<em>/{player.matches}</em></strong></div>
      <div><small>Own-baseline lift / 100</small><strong>{signed(player.lift_per100)}</strong></div>
    </div>
    <div className="rr-player-body">
      <div className="rr-player-interval"><div><strong>95% match-bootstrap interval</strong><span>Pooled score · adjusted runs / 100 balls</span></div>
        <div className="rr-interval-track"><i style={{left:point(player["boot_q0.25"])+"%"}}/><b style={{left:point(player.pooled)+"%"}}/></div>
        <div className="rr-interval-labels"><span>{fmt(low)}</span><span>Q25 {fmt(player["boot_q0.25"])}</span><span>{fmt(high)}</span></div>
      </div>
      <Split label="Format exposure" left={player.ipl_balls} right={player.t20i_balls} total={player.balls} labels={["IPL","T20I"]}/>
      <Split label="Pressure exposure" left={player.chase_balls} right={player.collapse_balls} total={player.balls} labels={["Chase","Collapse"]}/>
      <div className="rr-player-meta"><span>Chase-only rank <strong>{player.chase_rank == null ? "Ineligible" : "#" + player.chase_rank}</strong></span>
        <span>Bootstrap Q25 <strong>{fmt(player["boot_q0.25"])}</strong></span></div>
      <p className="rr-deployment"><b>RR deployment</b>{player.deployment}</p>
    </div>
  </article>;
}

function RankExplorer({ rows }) {
  const [role, setRole] = useState(roles[0]);
  const [rank, setRank] = useState(1);
  const [metric, setMetric] = useState("score");
  const [search, setSearch] = useState("");
  const group = rows.filter(p => p.role === role);
  const shown = group.filter(p => p.name.toLowerCase().includes(search.trim().toLowerCase()));
  const player = group.find(p => p.final_rank === rank);
  const [,,unit] = metrics.find(([id]) => id === metric) ?? metrics[0];
  const values = group.map(p => p[metric]);
  const min = Math.min(0, ...values);
  const max = Math.max(1, ...values);
  const position = n => 100 * (n - min) / (max - min);
  const zero = position(0);
  return <section id="rankings" className="rr-section" data-reveal>
    <div className="rr-section-top"><Heading index="THE SHORTLIST" title="Find your edge." detail="Twenty player files. Every rating, backed by the sample behind it."/>
      <Choices options={roles.map(r => [r,r])} value={role} onChange={r => {setRole(r); setRank(1);setSearch("");}} label="Player category"/>
    </div>
    <div className="rr-rank-grid">
      <Evidence id="official-rankings" query="shortlist" title="Official submission order" rows={shown} className="rr-panel">
        <div className="rr-rank-header"><div><h3>Official order</h3><small>{unit}</small></div>
          <Choices options={metrics} value={metric} onChange={setMetric} label="Displayed ranking metric"/></div>
        <label className="rr-player-search"><span aria-hidden="true">⌕</span><input type="search" aria-label="Find a shortlisted player" value={search} onChange={event=>setSearch(event.target.value)} placeholder="Find a player"/><span>{shown.length} / 10</span></label>
        <ol className="rr-rank-list" aria-label={role + " official order"}>
          {shown.map(p => {
            const end = position(p[metric]);
            return <li key={p.name}><button type="button" aria-pressed={rank === p.final_rank} onClick={() => setRank(p.final_rank)}>
              <span className="rr-rank-no">{String(p.final_rank).padStart(2,"0")}</span>
              <span className="rr-rank-name">{p.name}</span>
              <span className="rr-row-bar" aria-hidden="true">{min < 0 && <b style={{left:zero+"%"}}/>}
                <i style={{left:Math.min(zero,end)+"%",width:Math.abs(end-zero)+"%"}}/></span>
              <strong>{metric === "ipl_balls" ? p[metric] : fmt(p[metric])}</strong>
            </button></li>;
          })}
        </ol>
        {!shown.length && <p className="rr-empty">No shortlisted player matches “{search}”. <button type="button" onClick={()=>setSearch("")}>Clear search</button></p>}
        <p className="rr-small rr-rank-foot">Final rating sets the submission order for every metric view.</p>
      </Evidence>
      <Evidence id="selected-player" query="shortlist" title="Selected player evidence" rows={[player]}>
        <div aria-live="polite"><PlayerCard key={player.name} player={player}/></div>
      </Evidence>
    </div>
  </section>;
}

const duelModes = [
  ["score","Final rating","Adjusted runs per 100 balls","Hosein leads the official ranking by 0.44 points."],
  ["boot_q0.25","Bootstrap Q25","Adjusted runs per 100 balls","Bumrah leads at the 25th percentile of the match bootstrap."],
  ["ipl_balls","IPL exposure","Qualifying IPL balls","Bumrah has 89 more qualifying IPL balls in this sample."]
];

function RatingGap({ low, high }) {
  const limit = Math.ceil(Math.max(Math.abs(low), Math.abs(high)) / 10) * 10;
  const point = value => (value + limit) / (2 * limit) * 100;
  return <figure className="rr-gap">
    <figcaption>Middle 95% of the bootstrap rating gap <span>Bumrah minus Hosein</span></figcaption>
    <div className="rr-gap-axis" aria-hidden="true">
      <span style={{left:point(low)+"%",width:point(high)-point(low)+"%"}}/>
      <i/>
    </div>
    <div className="rr-gap-labels" aria-hidden="true"><span>−{limit} · Hosein leads</span><span>0</span><span>+{limit} · Bumrah leads</span></div>
  </figure>;
}

function Duel({ bowlers, totals }) {
  const [mode, setMode] = useState("score");
  const [,,unit,summary] = duelModes.find(([id]) => id === mode) ?? duelModes[0];
  const pair = bowlers.slice(0,2);
  const max = Math.max(...pair.map(p => p[mode])) * 1.06;
  return <section id="comparison" className="rr-section rr-duel" data-reveal>
    <div className="rr-duel-inner">
      <div className="rr-duel-intro"><Heading index="THE CLOSEST CALL" title="Two bowlers. One close call." detail="Hosein leads the official rating. Bumrah has the stronger IPL sample. Explore the trade-off."/>
        <div className="rr-duel-margin"><strong>0.44<span>pts</span></strong><p>separate the top two.<br/>The order stays uncertain.</p></div>
      </div>
      <div className="rr-duel-evidence">
      <Choices options={duelModes} value={mode} onChange={setMode} label="Bowler comparison metric"/>
      <Evidence id="bowler-duel" query="shortlist" title="Leading bowler comparison" rows={pair}>
        <div className="rr-duel-chart" aria-label={unit}>
          {pair.map((p,i) => <div className={"rr-duel-line rr-duel-"+i} key={p.name}>
            <b>{p.name}</b><div aria-hidden="true"><span style={{width:p[mode]/max*100+"%"}}/></div>
            <strong>{mode === "ipl_balls" ? p[mode] : fmt(p[mode])}</strong>
          </div>)}
        </div>
        <p className="rr-duel-caption" aria-live="polite"><span>{unit}</span>{summary}</p>
        <div className="rr-duel-facts">
          <span>Chase-only rank <b>Hosein #2 · Bumrah #1</b></span>
          <span>Positive matches <b>Hosein 15/19 · Bumrah 16/24</b></span>
          <span>Own-baseline lift / 100 <b>Hosein +41.56 · Bumrah +5.57</b></span>
        </div>
      </Evidence>
      <Evidence id="joint-bootstrap" query="screening" title="Joint fixture bootstrap" rows={[totals]}>
        <p className="rr-joint"><b>{pct(totals.bumrahAhead)}</b><span>Bumrah led in {pct(totals.bumrahAhead)} of {number.format(totals.draws)} draws across {totals.fixtures} fixtures. The middle 95% of the rating gap ran from {signed(totals.jointLow)} to {signed(totals.jointHigh)}, leaving the order uncertain.</span></p>
        <RatingGap low={totals.jointLow} high={totals.jointHigh}/>
      </Evidence>
      <div className="rr-leverage"><strong>Win-probability cross-check</strong><p>Bumrah +0.70 (+0.08 to +1.24), Hosein +0.07 (−0.32 to +0.47) percentage points per ball. The interval for the gap includes zero.</p></div>
      </div>
    </div>
  </section>;
}

function Auction({ comparators, plans, squad, scenario, setScenario }) {
  const plan = plans.find(row => row.id === scenario) ?? plans[0];
  return <section id="auction" className="rr-section" data-reveal>
    <Heading index="IPL 2027" title="RR auction plan" detail="Prioritise finishing depth. Keep Archer as the lead death bowler and assess seam cover after Curran’s trade."/>
    {squad && <Evidence id="auction-squad" query="auctionSquad" title="RR roster after retentions" rows={[squad]}
      headerControls={<p className="rr-auction-squad" data-reviewed-rows><b>₹{fmt(squad.purseCrore)} crore</b> remaining · {squad.openSlots} open slots · {squad.squadSize} players in the squad · <a href={squad.sourceHref} target="_blank" rel="noreferrer">RR’s squad announcement</a></p>} />}
    {plan ? <Evidence id="auction-plan" query="auctionPlan" title="Auction decisions after retentions" rows={[plan]}
      headerControls={<Choices options={plans.map(row => [row.id, row.label])} value={plan.id} onChange={setScenario} label="Auction scenario"/>}>
      <div className="rr-call" aria-live="polite">
        <div key={plan.id} className="rr-update"><div className="rr-kicker">{plan.label}</div><h3>{plan.title}</h3><p>{plan.decision}</p></div>
        {plan.candidate ? <>
          <div><strong>{fmt(plan.rating)}</strong><span>{plan.candidate} · historical rating</span></div>
          <div><strong>{plan.iplBalls}</strong><span>Qualifying IPL balls</span></div>
        </> : null}
      </div>
      <p className="rr-availability"><span/> {plan.status} <a href={plan.sourceHref} target="_blank" rel="noreferrer">{plan.sourceLabel}</a></p>
    </Evidence> : <p className="rr-availability">Auction scenarios are unavailable for this snapshot.</p>}
    <p className="rr-availability">Auction registration was unverified for the watchlist on 18 Nov 2026. The historical test did not establish predictive accuracy for future performance, and we have no model for winning bids or prices.</p>
    <Evidence id="auction-comparators" query="auction" title="Historical RR role comparisons" rows={comparators} className="rr-panel"
      headerControls={<div className="rr-table-header"><h3>Historical role benchmarks</h3><small>Final rating · adjusted runs / 100 balls</small></div>}>
      <div className="rr-table-wrap"><table>
        <thead><tr><th scope="col">Role</th><th scope="col">Benchmark</th><th scope="col">RR comparator</th><th scope="col">Gap</th></tr></thead>
        <tbody>{comparators.map(row => <tr key={row.label}><th scope="row">{row.label === "Pace fallback" ? "Pace" : row.label}</th><td>{row.target} <b>{fmt(row.targetScore)}</b></td><td>{row.incumbent} <b>{fmt(row.incumbentScore)}</b></td><td className={row.gap < 0 ? "rr-negative" : "rr-positive"}><b>{signed(row.gap)}</b></td></tr>)}</tbody>
      </table></div>
      <p className="rr-small rr-table-note">These comparisons describe past performance. Ferreira fell short of the sample threshold for a final rating.</p>
    </Evidence>
  </section>;
}

function Methodology({ robustness }) {
  const [window, setWindow] = useState(0);
  const [name, innings, balls, ballLabel, condition] = windows[window];
  return <section id="methods" className="rr-section" data-reveal>
    <Heading index="MODEL & VALIDATION" title="What counts as pressure?" detail="We read the score before each delivery and apply the same situations to both roles."/>
    <Choices options={windows.map(([label],i) => [i,label])} value={window} onChange={setWindow} label="Pressure window"/>
    <div className="rr-rule" aria-live="polite">
      <div key={window} className="rr-update"><span className="rr-kicker">{innings}</span><h3>{name}</h3><p>{condition}{window > 0 && " · At least 2 wickets in hand"}</p></div>
      <div><strong>{balls}</strong><span>{ballLabel}</span></div>
    </div>
    <div className="rr-method-grid">
      <article className="rr-panel rr-method"><h3>From ball to rating</h3><ol>
        <li><b>Value each ball.</b> Bat runs minus dismissal cost for batters. Credited wicket value minus charged runs for bowlers.</li>
        <li><b>Adjust for context.</b> Use earlier-date IPL or T20I expectations by innings, phase and match state, then adjust for the opponent.</li>
        <li><b>Check usual performance.</b> Compare with each player’s earlier ordinary adjusted rate after 120 ordinary balls. Report this lift alongside the final rating.</li>
        <li><b>Remove one match at a time.</b> Calculate 100 × remaining adjusted value ÷ (remaining balls + 60). Use the minimum. Each removal must leave 60 balls and eight qualifying matches.</li>
      </ol></article>
      <Evidence id="ranking-overlap" query="robustness" title="Final top-ten membership retained" rows={robustness} className="rr-panel">
        <div className="rr-table-header"><h3>How much of the top ten survives?</h3><small>Players retained from each final list</small></div>
        <div className="rr-table-wrap"><table><thead><tr><th scope="col">Sensitivity check</th>{robustness.map(r => <th key={r.role} scope="col">{r.role}</th>)}</tr></thead>
          <tbody>{[["chase","Chase-only"],["q25","Match bootstrap Q25"],["equal8","Equal-eight-match Q25"],["leverage","Win-probability leverage"]].map(([id,label]) =>
            <tr key={id}><th scope="row">{label}</th>{robustness.map(r => <td key={r.role}><b>{r[id]} / 10</b>
              <span className="rr-overlap-track" aria-hidden="true"><i style={{width:r[id]*10+"%"}}/></span>
            </td>)}</tr>)}</tbody></table></div>
      </Evidence>
    </div>
    <Evidence id="forecast-test" query="robustness" title="2026 forward test" rows={robustness} className="rr-panel rr-forecast">
      <div className="rr-table-header"><h3>Can the rating predict 2026?</h3><small>Forecast RMSE · lower is better</small></div>
      <div className="rr-table-wrap"><table><thead><tr><th scope="col">2026 cohort</th><th scope="col">Players</th><th scope="col">Zero baseline</th><th scope="col">Final rating</th><th scope="col">Bootstrap Q25</th><th scope="col">Final-rating Spearman</th></tr></thead>
        <tbody>{robustness.map(r => <tr key={r.role}><th scope="row">{r.role}</th><td>{r.players}</td><td><b>{fmt(r.zero)}</b></td><td>{fmt(r.deletion)}</td><td>{fmt(r.forecastQ25)}</td><td>{r.spearman.toFixed(3)}</td></tr>)}</tbody></table></div>
      <p className="rr-small rr-table-note">Zero predicts performance in line with context and opponent expectations. It had lower error in both roles. We repeatedly inspected 2026, and no parameter, rank or adjudication was preregistered. Use these ratings as a historical shortlist.</p>
    </Evidence>
  </section>;
}

export function DashboardContent() {
  const { canEdit, reviewedRows } = useDataApp();
  const root = useRef(/** @type {HTMLDivElement | null} */ (null));
  const [active, setActive] = useState("top");
  const [scenario, setScenario] = useState("finish");
  const publicViewer = !canEdit;
  const [appearance, setAppearance] = useState(readAppearance);
  const rows = reviewedRows("shortlist");
  const totals = reviewedRows("screening")[0];
  const comparators = reviewedRows("auction");
  const auctionPlans = reviewedRows("auctionPlan");
  const squad = reviewedRows("auctionSquad")[0];
  const robustness = reviewedRows("robustness");
  const matchEvidence = reviewedRows("matchEvidence");

  useLayoutEffect(() => {
    if (performance.getEntriesByType("navigation")[0]?.type === "back_forward") return;
    const section = nav.find(([id]) => window.location.hash === `#${id}`)?.[0];
    if (section) root.current?.querySelector(`#${section}`)?.scrollIntoView({ behavior: "instant" });
  }, []);

  useEffect(() => {
    const page = root.current;
    if (!page) return;
    const progress = page.querySelector(".rr-nav");
    const reveal = new IntersectionObserver(entries => {
      for (const entry of entries) {
        if (entry.isIntersecting) {
          entry.target.classList.add("rr-visible");
          reveal.unobserve(entry.target);
        }
      }
    }, {threshold:0.07});
    page.querySelectorAll("[data-reveal]").forEach(section => reveal.observe(section));
    const sections = Array.from(page.querySelectorAll(nav.map(([id]) => "#"+id).join(",")));
    const activeSections = new IntersectionObserver(entries => {
      for (const entry of entries) if (entry.isIntersecting) setActive(entry.target.id);
    }, {rootMargin:"-15% 0px -65% 0px",threshold:0});
    sections.forEach(section => activeSections.observe(section));
    let height = page.scrollHeight;
    const size = new ResizeObserver(() => {height=page.scrollHeight;schedule();});
    size.observe(page);
    let frame = 0;
    let previousProgress = "";
    const update = () => {
      frame = 0;
      const rect = page.getBoundingClientRect();
      const viewport = window.innerHeight;
      const traveled = Math.max(0, -rect.top);
      const total = Math.max(1, height - viewport);
      const nextProgress = Math.min(1,traveled/total).toFixed(4);
      if (progress instanceof HTMLElement && nextProgress !== previousProgress) {
        progress.style.setProperty("--rr-progress", nextProgress);previousProgress=nextProgress;
      }
    };
    function schedule() { if (!frame) frame = requestAnimationFrame(update); }
    document.addEventListener("scroll", schedule, {passive:true,capture:true});
    window.addEventListener("resize", schedule);
    update();
    return () => {
      reveal.disconnect();
      activeSections.disconnect();
      size.disconnect();
      cancelAnimationFrame(frame);
      document.removeEventListener("scroll", schedule, true);
      window.removeEventListener("resize", schedule);
    };
  }, []);

  function changeAppearance(next) {
    setAppearance(next);
    try { localStorage.setItem(appearanceKey, next); } catch {
      // Keep the change for the current visit.
    }
  }

  return <div ref={root} className="rr-page" data-rr-appearance={publicViewer ? appearance : undefined}>
    <a className="rr-skip" href="#analytics">Skip to analytics</a>
    <nav className="rr-nav" aria-label="Scouting dashboard">
      <a className="rr-brand" href="#top"><Mark/> Supe<span>RR</span></a>
      <div className="rr-nav-links">{nav.map(([id, name]) => <a key={id} href={"#"+id} aria-current={active === id ? "location" : undefined}>{name}</a>)}</div>
      {publicViewer ? <Picker label="Appearance" variant="theme" value={appearance} options={appearances}
        onChange={changeAppearance} /> : <span className="rr-round">ROUND 1 <b>•</b> IPL 2027</span>}
    </nav>
    <section id="top" className="rr-hero">
      <div className="rr-hero-art" aria-hidden="true"/><div className="rr-hero-grid" aria-hidden="true"/>
      <div className="rr-hero-light" aria-hidden="true"/>
      <div className="rr-hero-content">
        <div className="rr-kicker"><span/> THE RAJASTHAN ROYALS SCOUTING ROOM <b>/</b> ROUND 01</div>
        <h1>Under<br/><em>Pressure.</em></h1>
        <p>When the game turns, who stands up?<br/>Follow the evidence. Make the call.</p>
        <div className="rr-hero-actions"><a className="rr-primary" href="#analytics">Enter the analytics lab <span>↗</span></a><a className="rr-secondary" href="#rankings">Explore the shortlist <span>↓</span></a></div>
      </div>
      <span className="rr-hero-tag">IPL + T20I <b> / </b> REVIEWED 17 NOV 2026</span>
    </section>
    <Evidence id="analysis-coverage" query="screening" title="Screened match coverage" rows={[totals]}><div className="rr-coverage">{[[totals.matches,"matches screened"],[totals.events,"regulation events"],[totals.pressure,"pressure-window events"]].map(([n,label]) => <div key={label}><b>{number.format(n)}</b><span>{label}</span></div>)}<a href="#methods">Inside the model <span>↗</span></a></div>
    </Evidence>
    <Evidence id="opening-scouting-calls" query="shortlist" title="Opening scouting calls" rows={rows.filter(p => ["Heinrich Klaasen","Akeal Hosein"].includes(p.name))}>
      <div className="rr-leaders">
        <a href="#rankings"><small>01 / TOP BATTER <span>↗</span></small><div><strong>Heinrich<br/>Klaasen</strong><b>37.14</b></div><p>Leads the historical batting shortlist.</p></a>
        <a href="#comparison"><small>01 / TOP BOWLER <span>↗</span></small><div><strong>Akeal<br/>Hosein</strong><b>22.10</b></div><p>Leads the official bowling shortlist.</p></a>
        <a href="#auction" onClick={() => setScenario("finish")}><small>RR / AUCTION PRIORITY <span>↗</span></small><div><strong>Finishing<br/>depth</strong></div><p>Hetmyer was released. Ferreira provides cover.</p></a>
      </div>
    </Evidence>
    <AnalyticsLab rows={rows} matches={matchEvidence}/>
    <RankExplorer rows={rows}/>
    <Duel bowlers={rows.filter(p => p.role === "Bowlers")} totals={totals}/>
    <Auction comparators={comparators} plans={auctionPlans} squad={squad} scenario={scenario} setScenario={setScenario}/>
    <Methodology robustness={robustness}/>
    <Analyst/>
    <footer className="rr-footer"><a className="rr-brand" href="#top"><Mark/> Supe<span>RR</span></a><p>Round 1 scouting dossier and final recheck · 17 November 2026</p><a href="#top">Back to top ↑</a></footer>
  </div>;
}



