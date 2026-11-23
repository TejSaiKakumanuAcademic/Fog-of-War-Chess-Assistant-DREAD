import chess

from dread_analyzer import DreadAnalyzer
from opponent_uncertainty_counter import (
    UncertaintyResult,
    ScenarioMeasurement
)


class MockUncertaintyCounter:

    def evaluate_candidates(self, moves, ply):
        measurements = {
            "g1f3": (100, 160),
            "e2e4": (100, 80),
            "f1c4": (100, 125)
        }

        return [
            UncertaintyResult(
                candidate_move=move.uci(),
                calculation_status="estimated",
                scenario_measurements=(
                    ScenarioMeasurement(
                        *measurements[move.uci()]
                    ),
                )
            )
            for move in moves
        ]


def test_combined_results():

    analyzer = DreadAnalyzer(MockUncertaintyCounter())

    # OMINOUS recommendations with strategic scores
    recommendations = [
        (chess.Move.from_uci("g1f3"), 85),
        (chess.Move.from_uci("e2e4"), 62),
        (chess.Move.from_uci("f1c4"), 50)
    ]

    results = analyzer.analyze_candidate_moves(
        recommendations,
        ply=0
    )

    assert len(results) == 3

    expected_ominous = {
        "g1f3": 85,
        "e2e4": 62,
        "f1c4": 50
    }

    for result in results:
        assert result.ominous_score == (
            expected_ominous[result.candidate_move]
        )
        assert result.deception_score is not None
        assert result.calculation_status == "ok"

        print(
            f"Move: {result.candidate_move} | "
            f"OMINOUS: {result.ominous_score:+d} | "
            f"DREAD: {result.deception_score:+.3f}"
        )

    print("\nCombined DREAD analysis test passed!")


if __name__ == "__main__":
    test_combined_results()
