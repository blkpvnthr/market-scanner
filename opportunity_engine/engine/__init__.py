"""Engine: universe, scoring, ranking, planning, thesis and orchestration.

Research only. Not financial advice.
"""

from .pipeline import ScanResult, run_scan, evaluate_ticker
from .universe import build_universe, UniverseEntry
from .scorer import compute_scores, ScoringResult
from .ranker import rank_opportunities
from .entry_exit_engine import build_plan
from .thesis_generator import generate_thesis
from .opportunity_report import format_opportunity_md

__all__ = [
    "ScanResult",
    "run_scan",
    "evaluate_ticker",
    "build_universe",
    "UniverseEntry",
    "compute_scores",
    "ScoringResult",
    "rank_opportunities",
    "build_plan",
    "generate_thesis",
    "format_opportunity_md",
]
