"""
Placeholder health-score formula.

Isolated in this one module/function on purpose: once the team designs the
real scoring model, only `calculate_health_score` (and maybe `flag_from_score`)
needs to be replaced. Nothing else in the database/seeding code should change.
"""


def calculate_health_score(revenue, burn_rate, runway_months, growth_rate):
    """
    Turn a company's raw monthly metrics into a placeholder 0-100 score.

    THIS IS A STAND-IN FORMULA, not a validated model. It weights runway,
    growth, and burn efficiency by gut-feel percentages just so the rest of
    the pipeline (storage, history, flags) has real numbers to work with.
    """
    # Runway: 12+ months of cash left is "safe" -> full marks.
    runway_score = min(runway_months / 12, 1.0) * 40

    # Growth: 15%+ month-over-month growth is "great" -> full marks.
    # Negative growth contributes nothing (not a penalty beyond zero).
    growth_score = min(max(growth_rate, 0) / 0.15, 1.0) * 35

    # Burn efficiency: burning no more than revenue brought in -> full marks.
    if revenue <= 0:
        burn_score = 0
    else:
        burn_ratio = burn_rate / revenue
        burn_score = max(1 - min(burn_ratio, 2) / 2, 0) * 25

    score = runway_score + growth_score + burn_score
    return round(min(max(score, 0), 100), 1)


def flag_from_score(score):
    """Bucket a 0-100 score into a simple traffic-light flag."""
    if score >= 70:
        return "on_track"
    elif score >= 40:
        return "watch"
    else:
        return "at_risk"
