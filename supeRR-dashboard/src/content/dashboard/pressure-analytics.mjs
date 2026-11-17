export function preparePlayer(matches) {
  if (!matches.length) return null;
  const balls = matches.reduce((sum, match) => sum + match.balls, 0);
  const value = matches.reduce((sum, match) => sum + match.value, 0);
  return {
    balls, value,
    matches: [...matches].sort((a, b) => a.matchId - b.matchId),
    remaining: matches.map(match => ({ value: value - match.value, balls: balls - match.balls })),
  };
}

export function sensitivityRating(player, shrinkage = 60) {
  if (!player || !Number.isFinite(shrinkage) || shrinkage < 0) return null;
  const ratings = player.remaining.map(match => match.balls + shrinkage > 0
    ? 100 * match.value / (match.balls + shrinkage) : null);
  return ratings.some(value => value === null) ? null : Math.min(...ratings);
}

export function sensitivityCurve(player) {
  return Array.from({ length: 49 }, (_, i) => ({ addedBalls: i * 5, rating: sensitivityRating(player, i * 5) }));
}

export function chartDomain(values) {
  const finite = values.filter(Number.isFinite);
  if (!finite.length) return [0, 1];
  const low = Math.min(0, ...finite);
  const high = Math.max(0, ...finite);
  const step = Math.max(5, Math.ceil((high - low) / 25) * 5);
  return [Math.floor(low / step) * step, Math.ceil(high / step) * step || step];
}
