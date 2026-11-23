
from dataclasses import dataclass
from typing import Iterable

import chess

from deception_scorer import score_candidates


@dataclass(frozen=True)
class CandidateAnalysisResult:
    candidate_move: str
    ominous_score: int
    deception_score: float | None
    calculation_status: str
    scenario_count: int
    reason: str | None = None


class DreadAnalyzer:

    def __init__(self, uncertainty_counter):
        self.uncertainty_counter = uncertainty_counter

    def analyze_candidate_moves(
        self,
        candidates: Iterable[tuple[chess.Move, int]],
        ply: int
    ) -> list[CandidateAnalysisResult]:

        # Preserve OMINOUS's candidate moves and scores
        recommendations = list(candidates)

        if not recommendations:
            return []

        moves = [move for move, score in recommendations]

        # Ask Tej's counter to estimate uncertainty
        uncertainty_results = (
            self.uncertainty_counter.evaluate_candidates(
                moves,
                ply=ply
            )
        )

        # Ask Devlin's scorer to calculate deception
        deception_results = score_candidates(
            uncertainty_results
        )

        # Associate each result with its OMINOUS score
        scores_by_move = {
            result.candidate_move: result
            for result in deception_results
        }

        combined_results = []

        for move, ominous_score in recommendations:
            result = scores_by_move[move.uci()]

            combined_results.append(
                CandidateAnalysisResult(
                    candidate_move=move.uci(),
                    ominous_score=ominous_score,
                    deception_score=result.deception_score,
                    calculation_status=result.calculation_status,
                    scenario_count=result.scenario_count,
                    reason=result.reason
                )
            )

        return combined_results
