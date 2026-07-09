"""
Plain-English explanation for a company's flag.

Isolated from fade_score.py for the same reason health_score.py is isolated:
this is a heuristic for *wording*, not the scoring math, and it's the piece
most likely to get rewritten (better phrasing, more metrics, etc.) without
touching how scores/flags are computed or stored.
"""

# Healthy benchmarks for each input to calculate_health_score(), used only to
# describe how far a metric is from "healthy" — not to recompute the score.
#   - runway / growth targets match the caps in calculate_health_score exactly
#     (12 months, 15% MoM).
#   - burn's target is simplified to breakeven (burn == revenue) rather than
#     the formula's literal full-marks value (zero burn), since "don't burn
#     more than you make" is the plain-language version of that same idea.
HEALTHY_BENCHMARKS = {
    "runway_months": 12,
    "growth_rate": 0.15,
    "burn_to_revenue_ratio": 1.0,
}

_METRIC_LABELS = {
    "runway": "runway",
    "revenue_growth": "revenue growth",
    "burn_rate": "burn rate",
}


def _metric_gaps(revenue, burn_rate, runway_months, growth_rate):
    """
    One gap per formula input: 0 = exactly at the healthy benchmark,
    positive = worse than healthy (below target), negative = better than
    healthy (above target). Expressed as a fraction of the benchmark so the
    three inputs are comparable despite having different units.
    """
    runway_gap = (HEALTHY_BENCHMARKS["runway_months"] - runway_months) / HEALTHY_BENCHMARKS["runway_months"]
    growth_gap = (HEALTHY_BENCHMARKS["growth_rate"] - growth_rate) / HEALTHY_BENCHMARKS["growth_rate"]

    if revenue > 0:
        burn_ratio = burn_rate / revenue
        burn_gap = burn_ratio - HEALTHY_BENCHMARKS["burn_to_revenue_ratio"]
    else:
        burn_gap = float("inf")  # no revenue at all to weigh burn against

    return {
        "runway": runway_gap,
        "revenue_growth": growth_gap,
        "burn_rate": burn_gap,
    }


def _metric_phrase(metric, gap):
    label = _METRIC_LABELS[metric]

    if gap == float("inf"):
        return f"{label} is far above target"

    pct = round(abs(gap) * 100)

    if metric == "burn_rate":
        return f"{label} is {pct}% above target" if gap > 0 else f"{label} is {pct}% below target"
    return f"{label} fell {pct}% below target" if gap > 0 else f"{label} is {pct}% above target"


def _prefix(flag):
    if flag == "on_track":
        return "On track:"
    label = "follow-on" if flag == "follow_on" else flag
    return f"Flagged as {label}:"


def generate_flag_reason(flag, is_stale, days_since_report, revenue, burn_rate, runway_months, growth_rate):
    """
    One plain, non-technical sentence explaining `flag`.

    If `is_stale` is True (fading, not the underlying metrics, is what
    produced this flag), the sentence blames stale data instead of a metric.
    Otherwise it names whichever of runway / revenue growth / burn rate is
    furthest from its healthy benchmark (or closest, for an on-track/
    follow-on company).
    """
    prefix = _prefix(flag)

    if is_stale:
        return f"{prefix} no numbers reported in {days_since_report} days, so the score has faded."

    gaps = _metric_gaps(revenue, burn_rate, runway_months, growth_rate)

    if flag == "follow_on":
        metric, gap = min(gaps.items(), key=lambda kv: kv[1])
        return f"{prefix} {_metric_phrase(metric, gap)}, the strongest metric."
    elif flag == "risk":
        metric, gap = max(gaps.items(), key=lambda kv: kv[1])
        return f"{prefix} {_metric_phrase(metric, gap)}, the largest gap of any metric."
    else:  # on_track
        metric, _ = max(gaps.items(), key=lambda kv: kv[1])
        return f"{prefix} all metrics near target, though {_METRIC_LABELS[metric]} is closest to concerning."
