from opponent_uncertainty_counter import (
    UncertaintyResult,
    ScenarioMeasurement
)

from deception_scorer import score_candidate


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


if __name__ == "__main__":
    test_deception_integration()

