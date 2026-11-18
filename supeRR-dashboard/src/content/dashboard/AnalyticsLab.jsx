import React, { useId, useMemo, useState } from "react";
import { DataComponent } from "../../data-app-public.jsx";
import Picker from "./Picker.jsx";
import { chartDomain, preparePlayer, sensitivityCurve, sensitivityRating } from "./pressure-analytics.mjs";

const format = value => value == null ? "Unavailable" : value.toFixed(2);
const signed = value => (value >= 0 ? "+" : "−") + format(Math.abs(value));
const clamp = value => Math.max(0, Math.min(240, Math.round(value / 5) * 5));

function Curves({ primary, peer, first, second, strength, onChange }) {
  const gradient = useId().replaceAll(":", "");
  const curves = useMemo(() => [sensitivityCurve(primary), sensitivityCurve(peer)], [primary, peer]);
  const [min, max] = chartDomain(curves.flat().map(point => point.rating));
  const plot = { left: 52, right: 730, top: 28, bottom: 280 };
  const x = value => plot.left + value / 240 * (plot.right - plot.left);
  const y = value => plot.bottom - (value - min) / (max - min) * (plot.bottom - plot.top);
  const path = curve => curve.map((point, index) => `${index ? "L" : "M"}${x(point.addedBalls).toFixed(2)},${y(point.rating).toFixed(2)}`).join(" ");
  const primaryScore = sensitivityRating(primary, strength);
  const peerScore = sensitivityRating(peer, strength);
  function scrub(event) {
    const bounds = event.currentTarget.getBoundingClientRect();
    onChange(clamp(((event.clientX - bounds.left) / bounds.width * 760 - plot.left) / (plot.right - plot.left) * 240));
  }
  return <div className="rr-curve-wrap">
    <div className="rr-plot-meta"><span>Adjusted runs / 100 balls</span><span>Drag the chart to explore ↔</span></div>
    <svg className="rr-curve-chart" viewBox="0 0 760 324" role="img" aria-label={`Shrinkage sensitivity: ${first} ${format(primaryScore)}, ${second} ${format(peerScore)}, at ${strength} added balls`}
      onPointerDown={event => { event.currentTarget.setPointerCapture(event.pointerId); scrub(event); }}
      onPointerMove={event => { if (event.buttons === 1) scrub(event); }}>
      <defs><linearGradient id={gradient} x1="0" x2="0" y1="0" y2="1"><stop offset="0" stopColor="#f44d9b" stopOpacity=".24"/><stop offset="1" stopColor="#f44d9b" stopOpacity="0"/></linearGradient></defs>
      {Array.from({length:5}, (_, i) => min + (max - min) * i / 4).map(tick => <g key={tick}>
        <line x1={plot.left} x2={plot.right} y1={y(tick)} y2={y(tick)} className="rr-plot-grid"/>
        <text x={plot.left - 12} y={y(tick) + 4} textAnchor="end" className="rr-plot-label">{Math.round(tick)}</text>
      </g>)}
      {[0,60,120,180,240].map(tick => <text key={tick} x={x(tick)} y="308" textAnchor="middle" className="rr-plot-label">{tick}</text>)}
      <path d={`${path(curves[0])} L${plot.right},${y(min)} L${plot.left},${y(min)} Z`} fill={`url(#${gradient})`}/>
      <line x1={x(60)} x2={x(60)} y1={plot.top} y2={plot.bottom} className="rr-official-line"/>
      <text x={x(60) + 8} y="16" className="rr-plot-label">Official · 60</text>
      {curves.map((curve, i) => <path key={i} className={`rr-curve rr-curve-${i}`} d={path(curve)}/>)}
      <line x1={x(strength)} x2={x(strength)} y1={plot.top} y2={plot.bottom} className="rr-cursor-line"/>
      <circle cx={x(strength)} cy={y(primaryScore)} r="6" className="rr-chart-dot rr-chart-dot-primary"/>
      <circle cx={x(strength)} cy={y(peerScore)} r="6" className="rr-chart-dot rr-chart-dot-peer"/>
    </svg>
    <div className="rr-curve-legend"><span><i/>{first}</span><span><i/>{second} · dashed</span><small>Shrinkage · added balls</small></div>
  </div>;
}

function Contributions({ player, name }) {
  const [focus, setFocus] = useState(null);
  const games = player.matches;
  const [min, max] = chartDomain(games.map(game => game.value));
  const y = value => 104 - (value - min) / (max - min) * 88;
  const width = 630 / games.length;
  const current = games[focus ?? 0];
  return <div className="rr-contributions">
    <div className="rr-contribution-head"><div><h3>One match at a time.</h3><p>{name} · adjusted contribution by match</p></div>
      <output aria-live="polite">Match {String((focus ?? 0) + 1).padStart(2,"0")} <b>{signed(current.value)}</b><small>{current.balls} qualifying balls</small></output></div>
    <svg className="rr-match-chart" viewBox="0 0 680 132" role="group" aria-label={`${name} match contributions. Focus a bar to inspect its value.`}>
      <line x1="36" x2="666" y1={y(0)} y2={y(0)} className="rr-plot-grid"/>
      <text x="27" y={y(0)+4} textAnchor="end" className="rr-plot-label">0</text>
      {games.map((game, i) => <g key={game.matchId} tabIndex={0} role="button" aria-label={`Match ${i+1}, ${signed(game.value)} adjusted runs, ${game.balls} balls`}
        className="rr-match-mark" onPointerEnter={() => setFocus(i)} onFocus={() => setFocus(i)} onClick={() => setFocus(i)}
        onKeyDown={event => { if (event.key === "Enter" || event.key === " ") {event.preventDefault();setFocus(i);} }}>
        <rect x={36+i*width} y="8" width={width} height="112" fill="transparent"/>
        <rect x={37+i*width} y={Math.min(y(0),y(game.value))} width={Math.max(1,width-3)} height={Math.max(2,Math.abs(y(game.value)-y(0)))} rx="2"
          className={game.value >= 0 ? "rr-match-positive" : "rr-match-negative"} opacity={focus === null || focus === i ? 1 : .4}/>
      </g>)}
      <text x="36" y="129" className="rr-plot-label">01</text><text x="666" y="129" textAnchor="end" className="rr-plot-label">{games.length}</text>
    </svg>
    <p className="rr-chart-note">Match records ordered by supplied match ID. Bars show adjusted runs, not a chronological trend.</p>
  </div>;
}

export default function AnalyticsLab({ rows, matches }) {
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
  return <section id="analytics" className="rr-section rr-lab" data-reveal>
    <div className="rr-section-top"><header className="rr-heading"><div className="rr-kicker"><span/> THE ANALYTICS LAB</div><h2>Move it.<br/><em>Measure it.</em></h2><p>Change the assumptions. See exactly how the model responds.</p></header>
      <div className="rr-lab-status"><i/> Instant recalculation <span>Reviewed 17 Nov 2026 evidence</span></div></div>
    <div className="rr-lab-workspace">
      <aside className="rr-lab-controls" aria-label="Analytics controls">
        <div className="rr-choices" role="group" aria-label="Analytics player category">{["Batters","Bowlers"].map(item => <button type="button" key={item} aria-pressed={role===item} onClick={()=>changeRole(item)}>{item}</button>)}</div>
        <div className="rr-field">Player
          <Picker label="Player" variant="player" value={selected} options={playerOptions} onChange={changePlayer} />
        </div>
        <div className="rr-field">Compare with
          <Picker label="Compare with" variant="player" value={comparison}
            options={playerOptions.filter(option => option.value !== selected)} onChange={setComparison} />
        </div>
        <div className="rr-strength"><label htmlFor="rr-shrinkage">Shrinkage <output>{strength}<small>added balls</small></output></label>
          <input id="rr-shrinkage" type="range" min="0" max="240" step="5" value={strength} onChange={event=>setStrength(Number(event.target.value))}/>
          <div><span>0 · rawer</span><span>240 · more conservative</span></div>
        </div>
        <p className="rr-lab-definition">The rating removes each match in turn and keeps the lowest score. Added balls shrink that score toward zero. The official model uses <b>60</b>.</p>
        <button type="button" className="rr-reset" onClick={()=>setStrength(60)} disabled={strength===60}>↺ Reset to official model</button>
        <div className="rr-lab-scope">{strength===60 ? "Official 60-ball setting" : "Sensitivity scenario"}<span>Eligibility and adjusted match contributions stay fixed. The submission order does not change.</span></div>
      </aside>
      <div className="rr-lab-visuals">
        <DataComponent id="shrinkage-curves" queryId="matchEvidence" title="Player rating sensitivity" kind="custom" variant="plain" showHeading={false} sourceRows={source} displayRows={display}><div data-reviewed-rows>
            <div className="rr-live-scores"><div><span><i/>{selected}</span><strong>{format(score)}</strong></div><div><span><i/>{comparison}</span><strong>{format(other)}</strong></div><div className="rr-score-gap"><span>Rating gap</span><strong>{signed(score-other)}</strong></div></div>
            <Curves primary={primary} peer={peer} first={selected} second={comparison} strength={strength} onChange={setStrength}/>
          </div>
        </DataComponent>
        <DataComponent id="match-contributions" queryId="matchEvidence" title="Observed match contributions" kind="custom" variant="plain" showHeading={false} sourceRows={primary.matches} displayRows={primary.matches}><div data-reviewed-rows><Contributions key={selected} player={primary} name={selected}/></div>
        </DataComponent>
      </div>
    </div>
  </section>;
}
