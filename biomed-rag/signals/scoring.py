"""
Emergence Score Computation.

Computes a composite score (0-100) that quantifies how "emerging" a
relationship between two biomedical entities is.

Score breakdown (from PROJECT_SPECIFICATION.md §F4):
  - Nouveauté  (30%) : is the relation recent / new?
  - Vélocité   (30%) : how fast is the co-occurrence frequency growing?
  - Diversité  (20%) : how many independent sources (teams/countries)?
  - Impact     (20%) : proxy based on frequency magnitude

Each sub-score is normalised to [0, 100] then combined with the weights above.
"""

from __future__ import annotations

import math
from typing import Optional


# ---------------------------------------------------------------------------
# Weights (must sum to 1.0)
# ---------------------------------------------------------------------------
W_NOVELTY   = 0.30
W_VELOCITY  = 0.30
W_DIVERSITY = 0.20
W_IMPACT    = 0.20


# ---------------------------------------------------------------------------
# Sub-score helpers
# ---------------------------------------------------------------------------

def _novelty_score(previous_freq: int) -> float:
    """
    Novelty: 100 if the relation did not exist before, decreasing as
    previous frequency grows.

    Formula: 100 * exp(-0.3 * previous_freq)
    - previous_freq == 0  → 100  (brand new)
    - previous_freq == 1  → ~74
    - previous_freq == 5  → ~22
    - previous_freq >= 10 → ~5   (well established)
    """
    return 100.0 * math.exp(-0.3 * max(previous_freq, 0))


def _velocity_score(current_freq: int, previous_freq: int) -> float:
    """
    Velocity: measures relative growth.

    growth_ratio = (current - previous) / max(previous, 1)
    Capped at 100 via a sigmoid-like mapping so extreme ratios don't
    dominate.
    """
    if current_freq <= 0:
        return 0.0

    growth = (current_freq - previous_freq) / max(previous_freq, 1)

    if growth <= 0:
        return 0.0

    # Sigmoid mapping: score = 100 * (1 - exp(-0.5 * growth))
    # growth=1 → ~39,  growth=3 → ~78,  growth=5 → ~92, growth>=10 → ~99
    return 100.0 * (1.0 - math.exp(-0.5 * growth))


def _diversity_score(num_sources: int) -> float:
    """
    Diversity: rewards having multiple independent sources.

    Uses a log scale:
    - 1 source  → 0
    - 2 sources → ~44
    - 5 sources → ~83
    - 10+       → ~100
    """
    if num_sources <= 1:
        return 0.0

    # log2 mapping capped at 100
    return min(100.0, 100.0 * math.log2(num_sources) / math.log2(10))


def _impact_score(current_freq: int) -> float:
    """
    Impact proxy: higher absolute frequency → higher impact.

    In the absence of journal impact-factor data we use
    the raw co-occurrence count as a proxy.

    - freq=1  → 10
    - freq=5  → 51
    - freq=10 → 72
    - freq=20 → 89
    - freq≥50 → ~100
    """
    if current_freq <= 0:
        return 0.0

    return min(100.0, 100.0 * (1.0 - math.exp(-0.07 * current_freq)))


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_emergence_score(
    *,
    entity_a: str,
    entity_b: str,
    current_freq: int,
    previous_freq: int,
    num_sources: int = 1,
) -> float:
    """
    Compute a composite emergence score for an entity-pair relationship.

    Args:
        entity_a:       First entity label  (used for traceability, not scoring)
        entity_b:       Second entity label (used for traceability, not scoring)
        current_freq:   Co-occurrence count in the *current* time window
        previous_freq:  Co-occurrence count in the *previous* time window
        num_sources:    Number of independent sources (articles / teams)

    Returns:
        Float in [0, 100].  Higher = more "emerging".
    """
    novelty   = _novelty_score(previous_freq)
    velocity  = _velocity_score(current_freq, previous_freq)
    diversity = _diversity_score(num_sources)
    impact    = _impact_score(current_freq)

    score = (
        W_NOVELTY   * novelty
        + W_VELOCITY  * velocity
        + W_DIVERSITY * diversity
        + W_IMPACT    * impact
    )

    return round(min(100.0, max(0.0, score)), 2)


def classify_signal(score: float) -> str:
    """
    Classify a signal based on its emergence score.

    Returns one of:
        EMERGING_SIGNAL, ACCELERATING_TREND, STABLE, DECLINING
    """
    if score >= 70:
        return "EMERGING_SIGNAL"
    if score >= 50:
        return "ACCELERATING_TREND"
    if score >= 30:
        return "STABLE"
    return "DECLINING"