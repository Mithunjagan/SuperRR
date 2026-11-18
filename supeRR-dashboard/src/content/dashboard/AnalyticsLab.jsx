import React, { useId, useMemo, useState } from "react";
import { DataComponent } from "../../data-app-public.jsx";
import Picker from "./Picker.jsx";
import { chartDomain, preparePlayer, sensitivityCurve, sensitivityRating } from "./pressure-analytics.mjs";

const format = value => value == null ? "Unavailable" : value.toFixed(2);
const signed = value => (value >= 0 ? "+" : "−") + format(Math.abs(value));
const clamp = value => Math.max(0, Math.min(240, Math.round(value / 5) * 5));

function Curves({ primary, peer, first, second, strength, onChange, sourceRows, displayRows }) {
  const gradient = useId().replaceAll(":", "");
  const curves = useMemo(() => [sensitivityCurve(primary), sensitivityCurve(peer)], [primary, peer]);
  const [min, max] = chartDomain(curves.flat().map(point => point.rating));
  const plot = { left: 34, right: 493, top: 23, bottom: 158 };
  const x = value => plot.left + value / 240 * (plot.right - plot.left);
  const y = value => plot.bottom - (value - min) / (max - min) * (plot.bottom - plot.top);
  const path = curve => curve.map((point, index) => `${index ? "L" : "M"}${x(point.addedBalls).toFixed(2)},${y(point.rating).toFixed(2)}`).join(" ");
  const primaryScore = sensitivityRating(primary, strength);
  const peerScore = sensitivityRating(peer, strength);
  function scrub(event) {
    const transform = event.currentTarget.getScreenCTM();
    if (!transform) return;
    const point = new DOMPoint(event.clientX, event.clientY).matrixTransform(transform.inverse());
    onChange(clamp((point.x - plot.left) / (plot.right - plot.left) * 240));
  }
  function startScrubbing(event) {
    if (!event.isPrimary || event.button !== 0) return;
    event.preventDefault();
    event.currentTarget.setPointerCapture(event.pointerId);
    scrub(event);
  }
  const heading = <div className="rr-chart-heading"><h3>Rating sensitivity</h3><span>Adjusted runs / 100 balls</span></div>;
  return <DataComponent id="shrinkage-curves" queryId="matchEvidence" title="Player rating sensitivity" kind="custom"
    variant="plain" className="rr-lab-card" showHeading={false} headerControls={heading} sourceRows={sourceRows} displayRows={displayRows}><div data-reviewed-rows>
    <svg className="rr-curve-chart" viewBox="0 0 510 185" role="img" aria-label={`Shrinkage sensitivity: ${first} ${format(primaryScore)}, ${second} ${format(peerScore)}, at ${strength} added balls`}
      onPointerDown={startScrubbing}
      onPointerMove={event => { if (event.currentTarget.hasPointerCapture(event.pointerId)) scrub(event); }}>
      <defs><linearGradient id={gradient} x1="0" x2="0" y1="0" y2="1"><stop offset="0" stopColor="#f44d9b" stopOpacity=".24"/><stop offset="1" stopColor="#f44d9b" stopOpacity="0"/></linearGradient></defs>
      {Array.from({length:5}, (_, i) => min + (max - min) * i / 4).map(tick => <g key={tick}>
        <line x1={plot.left} x2={plot.right} y1={y(tick)} y2={y(tick)} className="rr-plot-grid"/>
        <text x={plot.left - 12} y={y(tick) + 4} textAnchor="end" className="rr-plot-label">{Math.round(tick)}</text>
      </g>)}
      {[0,60,120,180,240].map(tick => <text key={tick} x={x(tick)} y="178" textAnchor="middle" className="rr-plot-label">{tick}</text>)}
      <path d={`${path(curves[0])} L${plot.right},${y(min)} L${plot.left},${y(min)} Z`} fill={`url(#${gradient})`}/>
      <line x1={x(60)} x2={x(60)} y1={plot.top} y2={plot.bottom} className="rr-official-line"/>
      <text x={x(60) + 8} y="16" className="rr-plot-label">Official · 60</text>
      {curves.map((curve, i) => <path key={i} className={`rr-curve rr-curve-${i}`} d={path(curve)}/>)}
      <line x1={x(strength)} x2={x(strength)} y1={plot.top} y2={plot.bottom} className="rr-cursor-line"/>
      <circle cx={x(strength)} cy={y(primaryScore)} r="6" className="rr-chart-dot rr-chart-dot-primary"/>
      <circle cx={x(strength)} cy={y(peerScore)} r="6" className="rr-chart-dot rr-chart-dot-peer"/>
    </svg>
    <p className="rr-chart-note">Shrinkage (added balls). Drag the chart or use the slider to explore.</p>
    </div>
  </DataComponent>;
}

function Contributions({ player, name }) {
  const [focus, setFocus] = useState(null);
  const games = player.matches;
  const [min, max] = chartDomain(games.map(game => game.value));
  const y = value => 158 - (value - min) / (max - min) * 135;
  const width = 459 / games.length;
  const current = games[focus ?? 0];
  const heading = <div className="rr-chart-heading"><div><h3>Match contributions</h3><span>{name} · adjusted runs</span></div>
    <output aria-live="polite">Match {String((focus ?? 0) + 1).padStart(2,"0")} <b>{signed(current.value)}</b><small>{current.balls} qualifying balls</small></output></div>;
  return <DataComponent id="match-contributions" queryId="matchEvidence" title="Observed match contributions" kind="custom"
    variant="plain" className="rr-lab-card" showHeading={false} headerControls={heading} sourceRows={games} displayRows={games}><div data-reviewed-rows>
    <svg className="rr-match-chart" viewBox="0 0 510 185" role="group" aria-label={`${name} match contributions. Focus a bar to inspect its value.`}>
      <line x1="34" x2="493" y1={y(0)} y2={y(0)} className="rr-plot-grid"/>
      <text x="24" y={y(0)+4} textAnchor="end" className="rr-plot-label">0</text>
      {games.map((game, i) => <g key={game.matchId} tabIndex={0} role="button" aria-label={`Match ${i+1}, ${signed(game.value)} adjusted runs, ${game.balls} balls`}
        className="rr-match-mark" onPointerEnter={() => setFocus(i)} onFocus={() => setFocus(i)} onClick={() => setFocus(i)}
        onKeyDown={event => { if (event.key === "Enter" || event.key === " ") {event.preventDefault();setFocus(i);} }}>
        <rect x={34+i*width} y="20" width={width} height="142" fill="transparent"/>
        <rect x={35+i*width} y={Math.min(y(0),y(game.value))} width={Math.max(1,width-3)} height={Math.max(2,Math.abs(y(game.value)-y(0)))} rx="2"
          className={game.value >= 0 ? "rr-match-positive" : "rr-match-negative"} opacity={focus === null || focus === i ? 1 : .4}/>
      </g>)}
      <text x="34" y="178" className="rr-plot-label">01</text><text x="493" y="178" textAnchor="end" className="rr-plot-label">{games.length}</text>
    </svg>
    <p className="rr-chart-note">Bars follow match ID order. Hover or focus a bar for details.</p>
    </div>
  </DataComponent>;
}

export default function AnalyticsLab({ rows, matches, matchesThrough }) {
  const [role, setRole] = useState("Bowlers");
  const [selected, setSelected] = useState("Akeal Hosein");
  const [comparison, setComparison] = useState("Jasprit Bumrah");
  const [strength, setStrength] = useState(60);
  const players = rows.filter(row => row.role === role);
  const prepared = useMemo(() => Object.fromEntries(rows.map(row => [row.name, preparePlayer(matches.filter(game => game.name === row.name && game.role === row.role))])), [rows, matches]);
  const primary = prepared[selected], peer = prepared[comparison];
  const source = matches.filter(game => game.role === role && [selected, comparison].includes(game.name));
  const score = sensitivityRating(primary, strength), other = sensitivityRating(peer, strength);
  if (!primary || !peer || score == null || other == null) return <section id="analytics" className="rr-section"><h2>Analytics unavailable</h2><p>Reviewed match contributions are required for this view.</p></section>;
  function changeRole(next) {
    const group = rows.filter(row => row.role === next);
    setRole(next);setSelected(group[0].name);setComparison(group[1].name);
  }
  function changePlayer(next) {
    if (next === comparison) setComparison(selected);
    setSelected(next);
  }
  const playerOptions = players.map(({ name }) => ({ value: name, label: name }));
  const display = [selected, comparison].map(name => ({name, addedBalls:strength, sensitivityRating:sensitivityRating(prepared[name], strength), officialRating:sensitivityRating(prepared[name],60)}));
  return <section id="analytics" className="rr-section rr-lab" aria-labelledby="rr-analytics-title">
    <header className="rr-lab-header"><h2 id="rr-analytics-title">Analytics</h2><p>{matchesThrough ? `Match data through ${matchesThrough}` : "Reviewed 17 Nov 2026"}</p></header>
    <div className="rr-lab-workspace">
      <aside className="rr-lab-controls" aria-label="Analytics controls">
        <div className="rr-field rr-lab-category">Role
          <div className="rr-choices" role="group" aria-label="Analytics player category">{["Batters","Bowlers"].map(item => <button type="button" key={item} aria-pressed={role===item} onClick={()=>changeRole(item)}>{item}</button>)}</div>
        </div>
        <div className="rr-field">Player
          <Picker label="Player" variant="player" value={selected} options={playerOptions} onChange={changePlayer} />
        </div>
        <div className="rr-field">Compare with
          <Picker label="Compare with" variant="player" value={comparison}
            options={playerOptions.filter(option => option.value !== selected)} onChange={setComparison} />
        </div>
        <div className="rr-lab-adjustment">
          <div className="rr-strength"><label htmlFor="rr-shrinkage">Shrinkage <output>{strength} added balls</output></label>
            <input id="rr-shrinkage" type="range" min="0" max="240" step="5" value={strength} onChange={event=>setStrength(Number(event.target.value))}/>
            <div><span>0 · no shrinkage</span><span>240 · more shrinkage</span></div>
          </div>
          <button type="button" className="rr-reset" onClick={()=>setStrength(60)} disabled={strength===60}>Reset to 60</button>
        </div>
      </aside>
      <div className="rr-live-scores"><div><span><i/>{selected} · solid line</span><strong>{format(score)}</strong></div><div><span><i/>{comparison} · dashed line</span><strong>{format(other)}</strong></div><div className="rr-score-gap"><span>Rating gap</span><strong>{signed(score-other)}</strong></div></div>
      <div className="rr-lab-visuals">
        <Curves primary={primary} peer={peer} first={selected} second={comparison} strength={strength} onChange={setStrength}
          sourceRows={source} displayRows={display} />
        <Contributions key={selected} player={primary} name={selected} />
      </div>
      <footer className="rr-lab-summary"><strong>{strength===60 ? "Official 60-ball setting" : "Sensitivity scenario"}</strong><p>The rating keeps the lowest score after leaving each match out in turn. Added balls pull that score toward zero. Eligibility, match contributions, and submission order stay fixed.</p></footer>
    </div>
  </section>;
}
