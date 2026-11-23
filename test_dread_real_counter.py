from dread_analyzer import DreadAnalyzer
from opponent_uncertainty_counter import OpponentUncertaintyCounter
import chess


def test_real_counter():

    # Initialize Tej's real uncertainty counter
    # White is the assisted player
    counter = OpponentUncertaintyCounter(
        assisted_color=chess.WHITE
    )

    # Connect it to DreadAnalyzer
    analyzer = DreadAnalyzer(counter)

    # Legal opening candidates for White
    candidates = [
        chess.Move.from_uci("g1f3"),
        chess.Move.from_uci("e2e4"),
        chess.Move.from_uci("d2d4")
    ]


    # Inspect the raw uncertainty estimates
    raw_results = counter.evaluate_candidates(
        candidates,
        ply=0
    )

    for result in raw_results:
        print(f"\nCandidate: {result.candidate_move}")
        print(f"Status: {result.calculation_status}")
        print(f"Scenarios: {result.scenario_count}")
        print(f"States explored: {result.states_explored}")
        print(f"Processing time: {result.processing_time_seconds:.4f}s")

        for i, scenario in enumerate(
            result.scenario_measurements, start=1
        ):
            print(
                f"  Scenario {i}: "
                f"{scenario.before} -> {scenario.after}"
            )

    # Analyze the starting position (ply 0)
    results = analyzer.analyze_candidate_moves(
        candidates,
        ply=0
    )

    for result in results:
        print(
            f"Move: {result.candidate_move} | "
            f"Score: {result.deception_score} | "
            f"Status: {result.calculation_status}"
        )

    assert len(results) == len(candidates)

    print("Real-counter integration test completed!")


if __name__ == "__main__":
    test_real_counter()
