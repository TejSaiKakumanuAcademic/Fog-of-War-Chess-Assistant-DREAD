from opponent_uncertainty_counter import (
    UncertaintyResult,
    ScenarioMeasurement
)

from deception_scorer import score_candidate, score_candidates


def test_deception_integration():

    # Create a simulated result using Tej's actual data structures
    uncertainty = UncertaintyResult(
        candidate_move="g1f3",
        calculation_status="estimated",
        scenario_measurements=(
            ScenarioMeasurement(before=40, after=20),
            ScenarioMeasurement(before=60, after=90),
            ScenarioMeasurement(before=100, after=200)
        )
    )

    # Pass Tej's result into Devlin's Deception Scorer
    result = score_candidate(uncertainty)

    # Display the result
    print("Candidate move:", result.candidate_move)
    print("Deception score:", result.deception_score)
    print("Scenarios evaluated:", result.scenario_count)
    print("Calculation status:", result.calculation_status)

    # Verify that the returned values are correct
    assert result.candidate_move == "g1f3"
    assert result.deception_score is not None
    assert abs(result.deception_score - 0.1949875) < 0.001
    assert result.scenario_count == 3
    assert result.calculation_status == "ok"

    print("Integration test passed!")


def test_multiple_candidates():

    # Simulate uncertainty results for three OMINOUS moves
    uncertainty_results = [
        UncertaintyResult(
            candidate_move="g1f3",
            calculation_status="estimated",
            scenario_measurements=(
                ScenarioMeasurement(before=100, after=160),
            )
        ),

        UncertaintyResult(
            candidate_move="e2e4",
            calculation_status="estimated",
            scenario_measurements=(
                ScenarioMeasurement(before=100, after=80),
            )
        ),

        UncertaintyResult(
            candidate_move="f1c4",
            calculation_status="estimated",
            scenario_measurements=(
                ScenarioMeasurement(before=100, after=125),
            )
        )
    ]

    # Calculate deception scores for all candidates
    results = score_candidates(uncertainty_results)

    expected_scores = {
        "g1f3": 0.678071905,
        "e2e4": -0.321928095,
        "f1c4": 0.321928095
    }

    assert len(results) == 3

    for result in results:
        expected = expected_scores[result.candidate_move]

        assert result.deception_score is not None
        assert abs(result.deception_score - expected) < 0.001
        assert result.scenario_count == 1
        assert result.calculation_status == "ok"

        print(
            f"Move: {result.candidate_move} | "
            f"Deception score: {result.deception_score:+.3f} | "
            f"Status: {result.calculation_status}"
        )

    print("Multiple candidate integration test passed!")
    
if __name__ == "__main__":
    test_deception_integration()
    print()
    test_multiple_candidates()