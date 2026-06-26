"""Statistical helpers for win-rate analysis (pure stdlib)."""
import math

Z_95 = 1.96
Z_99 = 2.576


def _norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def wilson_interval(successes: int, n: int, z: float = Z_95) -> tuple[float, float]:
    """Wilson score 95% CI for a binomial proportion. Returns (low, high) in [0, 1]."""
    if n <= 0:
        return 0.0, 0.0
    p_hat = successes / n
    z2 = z * z
    denom = 1 + z2 / n
    center = p_hat + z2 / (2 * n)
    margin = z * math.sqrt((p_hat * (1 - p_hat) + z2 / (4 * n)) / n)
    return max(0.0, (center - margin) / denom), min(1.0, (center + margin) / denom)


def _binom_pmf(k: int, n: int, p: float) -> float:
    return math.comb(n, k) * (p ** k) * ((1 - p) ** (n - k))


def binom_test_two_sided(successes: int, n: int, p0: float) -> float:
    """Exact two-sided binomial test (feasible for typical sample sizes here)."""
    if n <= 0:
        return 1.0
    p0 = min(max(p0, 1e-9), 1 - 1e-9)
    if n > 200:
        return _binom_z_test_two_sided(successes, n, p0)
    p_obs = _binom_pmf(successes, n, p0)
    total = 0.0
    for k in range(n + 1):
        if _binom_pmf(k, n, p0) <= p_obs + 1e-15:
            total += _binom_pmf(k, n, p0)
    return min(1.0, total)


def binom_test_greater(successes: int, n: int, p0: float) -> float:
    """One-sided P(X >= successes | p = p0)."""
    if n <= 0:
        return 1.0
    p0 = min(max(p0, 1e-9), 1 - 1e-9)
    if n > 200:
        return 1.0 - _norm_cdf((successes - 0.5 - n * p0) / math.sqrt(n * p0 * (1 - p0)))
    total = 0.0
    for k in range(successes, n + 1):
        total += _binom_pmf(k, n, p0)
    return min(1.0, total)


def binom_test_less(successes: int, n: int, p0: float) -> float:
    """One-sided P(X <= successes | p = p0)."""
    if n <= 0:
        return 1.0
    p0 = min(max(p0, 1e-9), 1 - 1e-9)
    if n > 200:
        return _norm_cdf((successes + 0.5 - n * p0) / math.sqrt(n * p0 * (1 - p0)))
    total = 0.0
    for k in range(successes + 1):
        total += _binom_pmf(k, n, p0)
    return min(1.0, total)


def _binom_z_test_two_sided(successes: int, n: int, p0: float) -> float:
    se = math.sqrt(p0 * (1 - p0) / n)
    if se == 0:
        return 1.0
    z = abs(successes / n - p0) / se
    return 2.0 * (1.0 - _norm_cdf(z))


def significance_label(p_value: float) -> str:
    if p_value < 0.01:
        return 'strong'
    if p_value < 0.05:
        return 'moderate'
    if p_value < 0.10:
        return 'weak'
    return 'none'


def analyze_win_rate(
    wins: int,
    n: int,
    baseline: float,
    *,
    min_n_for_test: int = 1,
) -> dict:
    """
    Analyze wins/n vs league baseline (proportion, e.g. 0.485 for 48.5%).

    Returns win-rate %, Wilson CI, p-values, and significance flags.
    """
    if n <= 0:
        return {
            'win_rate': 0.0,
            'ci_low': 0.0,
            'ci_high': 0.0,
            'p_value': 1.0,
            'p_value_greater': 1.0,
            'p_value_less': 1.0,
            'sig_label': 'none',
            'sig_advantage': False,
            'sig_disadvantage': False,
            'baseline_wr': round(100 * baseline, 1),
            'ci_low_score': 0.0,
        }

    rate = wins / n
    ci_low, ci_high = wilson_interval(wins, n)
    baseline = min(max(baseline, 1e-9), 1 - 1e-9)

    if n < min_n_for_test:
        p_two = p_greater = p_less = 1.0
    else:
        p_two = binom_test_two_sided(wins, n, baseline)
        p_greater = binom_test_greater(wins, n, baseline)
        p_less = binom_test_less(wins, n, baseline)

    sig_label = significance_label(min(p_greater, p_less) if rate != baseline else p_two)

    # Advantage: one-sided p < 0.05 AND Wilson CI lower bound above baseline
    sig_advantage = p_greater < 0.05 and ci_low > baseline
    sig_disadvantage = p_less < 0.05 and ci_high < baseline

    return {
        'win_rate': round(100 * rate, 1),
        'ci_low': round(100 * ci_low, 1),
        'ci_high': round(100 * ci_high, 1),
        'p_value': round(p_two, 4),
        'p_value_greater': round(p_greater, 4),
        'p_value_less': round(p_less, 4),
        'sig_label': sig_label if (sig_advantage or sig_disadvantage) else 'none',
        'sig_advantage': sig_advantage,
        'sig_disadvantage': sig_disadvantage,
        'baseline_wr': round(100 * baseline, 1),
        'ci_low_score': ci_low,
    }
