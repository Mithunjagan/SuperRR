import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { test } from "node:test";
import { preparePlayer, sensitivityRating, sensitivityCurve, chartDomain } from "../../supeRR-dashboard/src/content/dashboard/pressure-analytics.mjs";

const snapshot = JSON.parse(await readFile(new URL("../../supeRR-dashboard/src/data.json", import.meta.url), "utf8"));
const shortlist = snapshot.queries.shortlist.rows;
const matches = snapshot.queries.matchEvidence.rows;

test("the interactive 60-ball setting reproduces every official shortlist rating", () => {
  assert.equal(shortlist.length, 20);
  for (const row of shortlist) {
    const source = matches.filter(match => match.name === row.name && match.role === row.role);
    const prepared = preparePlayer(source);
    assert.equal(prepared.balls, row.balls, row.name);
    assert.equal(source.filter(match => match.balls > 0).length, row.matches, row.name);
    assert.ok(Math.abs(sensitivityRating(prepared,60) - row.score) < .000001, row.name);
    assert.ok(Math.abs(100 * prepared.value / (prepared.balls + 60) - row.pooled) < .000001, row.name);
  }
});

test("changing shrinkage recalculates each deletion, preserving fixed evidence", () => {
  for (const row of shortlist) {
    const player = preparePlayer(matches.filter(match => match.name === row.name));
    const before = JSON.stringify(player);
    const curve = sensitivityCurve(player);
    assert.equal(curve.length,49);
    assert.equal(curve[0].addedBalls,0);
    assert.equal(curve.at(-1).addedBalls,240);
    assert.ok(curve.every(point => Number.isFinite(point.rating)));
    assert.ok(Math.abs(curve[12].rating-row.score)<.000001);
    assert.ok(Math.abs(curve.at(-1).rating)<=Math.abs(curve[0].rating));
    assert.equal(JSON.stringify(player),before);
  }
});

test("zero-exposure match values remain in deletion calculations", () => {
  const player=preparePlayer([
    {matchId:2,value:5,balls:20}, {matchId:1,value:-4,balls:0}, {matchId:3,value:15,balls:40},
  ]);
  assert.equal(player.balls,60);
  assert.equal(player.value,16);
  assert.deepEqual(player.matches.map(match=>match.matchId),[1,2,3]);
  assert.equal(sensitivityRating(player,60),1.25);
  assert.equal(sensitivityRating(player,0),5);
});

test("missing evidence and invalid assumptions do not produce fabricated scores", () => {
  assert.equal(preparePlayer([]),null);
  assert.equal(sensitivityRating(null),null);
  const player=preparePlayer([{matchId:1,value:4,balls:4}]);
  for(const strength of [-1,NaN,Infinity]) assert.equal(sensitivityRating(player,strength),null);
  assert.equal(sensitivityRating(player,0),null);
  assert.deepEqual(chartDomain([]),[0,1]);
  const [low,high]=chartDomain([-12,7]);
  assert.ok(low<=-12 && high>=7);
});
