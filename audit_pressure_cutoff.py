"""Adversarial check that future outcomes cannot change earlier fits or frozen expectations."""
import numpy as np
from pandas.testing import assert_series_equal

import rank_pressure as model

CUTOFF = "2025-01-01"

def audit():
    original = model.f
    future = original.match_date.ge(CUTOFF)
    modified = original.copy()
    for column in ("runs", "bowl_runs"):
        modified.loc[future, column] += 10
    for column in ("bat_out", "bowl_wicket"):
        modified.loc[future, column] = ~modified.loc[future, column]
    for role in model.ROLE_COLUMNS:
        baseline = model.score(role, cutoff=CUTOFF)
        try:
            model.f = modified
            changed = model.score(role, cutoff=CUTOFF)
        finally:
            model.f = original
        past = baseline.match_date.lt(CUTOFF)
        assert_series_equal(baseline.loc[past, "performance"], changed.loc[past, "performance"])
        assert_series_equal(baseline.ordinary_rating, changed.ordinary_rating)
        assert_series_equal(baseline.eligible_event, changed.eligible_event)
        np.testing.assert_allclose(baseline.v - baseline.performance, changed.v - changed.performance, atol=1e-12)
        np.testing.assert_allclose(changed.v - baseline.v, changed.performance - baseline.performance, atol=1e-12)
        eligible = baseline[baseline.pressure & baseline.eligible_event]
        match_rows = model.per_match(eligible)
        print(role, "passed future outcome perturbation; zero-exposure match rows:",
              int(match_rows.balls.eq(0).sum()))

if __name__ == "__main__":
    audit()

