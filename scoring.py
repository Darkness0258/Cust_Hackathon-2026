from data_loader import get_sector_win_rate, get_sector_budget_range


def _score_compliance(compliance_pct: float) -> float:
    """
    Factor 1 — Compliance % (35 points max)
    Linear scale: 100% compliance = 35pts, 0% = 0pts
    """
    return round((compliance_pct / 100) * 35, 4)


def _score_gaps(gaps_count: int) -> float:
    """
    Factor 2 — Gaps Found (25 points max)
    0 gaps = 25 | 1-2 = 20 | 3-4 = 13 | 5+ = 5
    """
    if gaps_count == 0:
        return 25.0
    elif gaps_count <= 2:
        return 20.0
    elif gaps_count <= 4:
        return 13.0
    else:
        return 5.0


def _score_sector(sector: str) -> float:
    """
    Factor 3 — Sector Match (20 points max)
    Based on historical win rate in this sector from bid history.
    win_rate 0.0-1.0 maps to 0-20 pts
    """
    win_rate = get_sector_win_rate(sector)
    return round(win_rate * 20, 4)


def _score_budget(budget_pkr: int, sector: str) -> float:
    """
    Factor 4 — Budget Range (20 points max)
    Full 20pts if budget is within historical win range for sector.
    Partial score if outside range (proportional distance penalty).
    0pts if budget is 0 (not stated).
    """
    if budget_pkr <= 0:
        return 10.0  # neutral — no budget info, give half points

    min_budget, max_budget = get_sector_budget_range(sector)

    # If no historical wins exist for sector, give neutral score
    if max_budget == float("inf"):
        return 10.0

    if min_budget <= budget_pkr <= max_budget:
        return 20.0

    # Budget is outside range — calculate penalty
    if budget_pkr < min_budget:
        # Too low — how far below minimum?
        ratio = budget_pkr / min_budget
    else:
        # Too high — how far above maximum?
        ratio = max_budget / budget_pkr

    # ratio is 0.0-1.0, scale to 0-15 pts (never full 20 if outside range)
    return round(ratio * 15, 4)


def calculate_win_probability(
    compliance_pct: float,
    gaps_count: int,
    sector: str,
    budget_pkr: int
) -> dict:
    """
    Calculate win probability using 4-factor weighted algorithm.

    Returns:
    {
        "win_probability": int (0-100),
        "budget_score": int (0-100),
        "capability_score": int (0-100),
        "decision": str,
        "factor_breakdown": {
            "compliance_pts": float,
            "gaps_pts": float,
            "sector_pts": float,
            "budget_pts": float
        }
    }
    """
    compliance_pts = _score_compliance(compliance_pct)
    gaps_pts = _score_gaps(gaps_count)
    sector_pts = _score_sector(sector)
    budget_pts = _score_budget(budget_pkr, sector)

    # Raw win probability (sum of all factors = max 100)
    raw_score = compliance_pts + gaps_pts + sector_pts + budget_pts
    win_probability = min(100, max(0, round(raw_score)))

    # Budget score (0-100 scale for frontend display)
    # Factor 4 is out of 20 pts — scale to 100
    budget_score = min(100, max(0, round(budget_pts * 5)))

    # Capability score (0-100 scale for frontend display)
    # Factors 1+2 combined = max 60 pts — scale to 100
    capability_raw = compliance_pts + gaps_pts
    capability_score = min(100, max(0, round((capability_raw / 60) * 100)))

    # GO/NO-GO decision
    if win_probability >= 65:
        margin = "HIGH MARGIN" if win_probability >= 80 else "MODERATE MARGIN"
        decision = f"GO-DECISION ({margin})"
    elif win_probability >= 50:
        decision = "REVIEW-DECISION (BORDERLINE)"
    else:
        decision = "NO-GO DECISION (HIGH RISK)"

    return {
        "win_probability": win_probability,
        "budget_score": budget_score,
        "capability_score": capability_score,
        "decision": decision,
        "factor_breakdown": {
            "compliance_pts": compliance_pts,
            "gaps_pts": gaps_pts,
            "sector_pts": sector_pts,
            "budget_pts": budget_pts
        }
    }