from dread_analyzer import DreadAnalyzer

from opponent_uncertainty_counter import (
    UncertaintyResult,
    ScenarioMeasurement
)

class MockUncertaintyCounter:

    def __init__(self):
        self.received_candidates = None
        self.received_ply = None

    def evaluate_candidates(self, candidates, ply=None):

        # Record what DreadAnalyzer actually passed
        self.received_candidates = list(candidates)
        self.received_ply = ply

        # Simulated uncertainty measurements
        measurements = {
            "g1f3": (100, 160),
            "e2e4": (100, 80),
            "f1c4": (100, 125)
        }

        results = []

        for move in candidates:
            before, after = measurements[move]

            results.append(
                UncertaintyResult(
                    candidate_move=move,
                    calculation_status="estimated",
                    scenario_measurements=(
                        ScenarioMeasurement(
                            before=before,
                            after=after
                        ),
                    )
                )
            )

        return results

def test_dread_analyzer():

    # Create a mock counter
    mock_counter = MockUncertaintyCounter()

    # Initialize DreadAnalyzer
    analyzer = DreadAnalyzer(mock_counter)

    # Simulated OMINOUS candidate moves
    candidates = ["g1f3", "e2e4", "f1c4"]

    # Analyze all candidate moves
    results = analyzer.analyze_candidate_moves(
        candidates,
        ply=0
    )

    assert mock_counter.received_candidates == candidates
    assert mock_counter.received_ply == 0

    # Verify three results were returned
    assert len(results) == 3

    # Expected deception scores
    expected_scores = {
        "g1f3": 0.678071905,
        "e2e4": -0.321928095,
        "f1c4": 0.321928095
    }

    for result in results:

        expected = expected_scores[result.candidate_move]

        assert result.deception_score is not None
        assert abs(result.deception_score - expected) < 0.001
        assert result.calculation_status == "ok"

        print(
            f"Move: {result.candidate_move} | "
            f"Deception Score: {result.deception_score:+.3f} | "
            f"Status: {result.calculation_status}"
        )

    print("DreadAnalyzer test passed!")


if __name__ == "__main__":
    test_dread_analyzer()
