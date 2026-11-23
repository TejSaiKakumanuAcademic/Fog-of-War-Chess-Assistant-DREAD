import chess

from fow_chess import FowBoard
from board_state_limiter import observe_board
from opponent_uncertainty_counter import (
    OpponentUncertaintyCounter,
    AssistedTurnEvent
)
from dread_analyzer import DreadAnalyzer


def test_multiturn():

    # Actual board used ONLY to generate test observations
    actual_board = FowBoard()

    # DREAD's independent uncertainty model
    counter = OpponentUncertaintyCounter(
        assisted_color=chess.WHITE,
        max_positions=25000
    )

    analyzer = DreadAnalyzer(counter)

    # ----------------------------------------
    # Move 1: White plays e2e4
    # ----------------------------------------

    white_move = chess.Move.from_uci("e2e4")
    actual_board.push(white_move)

    white_event = AssistedTurnEvent(
        ply=1,
        own_move=white_move
    )

    result = counter.update_model(white_event)

    print("After White e2e4:")
    print("Update status:", result.status)
    print("Current ply:", counter.ply)
    print("States explored:", result.states_explored)

    assert result.status == "applied"
    assert counter.ply == 1

    # ----------------------------------------
    # Move 2: Black plays e7e5
    # ----------------------------------------

    black_move = chess.Move.from_uci("e7e5")
    actual_board.push(black_move)

    # Capture only what White is allowed to see
    white_observation = observe_board(
        actual_board,
        chess.WHITE
    )

    black_event = AssistedTurnEvent(
        ply=2,
        observation=white_observation
    )

    result = counter.update_model(black_event)

    print("\nAfter Black e7e5:")
    print("Update status:", result.status)
    print("Current ply:", counter.ply)
    print("States explored:", result.states_explored)

    assert result.status == "applied", result.reason
    assert counter.ply == 2

    # ----------------------------------------
    # White requests DREAD analysis
    # ----------------------------------------

    candidates = [
        chess.Move.from_uci("g1f3"),
        chess.Move.from_uci("f1c4"),
        chess.Move.from_uci("d2d4")
    ]

    inspect_black_visibility(actual_board, candidates)

    # Make sure the candidates are legal
    for move in candidates:
        assert move in actual_board.fow_legal_moves

    # Evaluate actual uncertainty estimates
    raw_results = counter.evaluate_candidates(
        candidates,
        ply=2
    )

    print("\nRaw uncertainty measurements:")

    for result in raw_results:
        print(
            f"\nMove: {result.candidate_move}"
            f" | Status: {result.calculation_status}"
            f" | Scenarios: {result.scenario_count}"
            f" | Explored: {result.states_explored}"
            f" | Time: {result.processing_time_seconds:.4f}s"
        )

        for scenario in result.scenario_measurements:
            print(
                f"  {scenario.before} -> {scenario.after}"
            )

        if result.reason:
            print("Reason:", result.reason)

    
        # Simulated OMINOUS scores for the candidate moves
        ominous_recommendations = [
            (chess.Move.from_uci("g1f3"), 85),
            (chess.Move.from_uci("f1c4"), 62),
            (chess.Move.from_uci("d2d4"), 50)
        ]

        scores = analyzer.analyze_candidate_moves(
            ominous_recommendations,
            ply=counter.ply
        )

    
    print("\nCombined OMINOUS + DREAD results:")

    for result in scores:
        print(
            f"Move: {result.candidate_move} | "
            f"OMINOUS: {result.ominous_score:+d} | "
            f"DREAD: {result.deception_score:+.3f} | "
            f"Status: {result.calculation_status}"
        )

    assert len(scores) == len(ominous_recommendations)
    assert counter.ply == 2


    for score in scores:
        print(
            f"Move: {score.candidate_move}"
            f" | Score: {score.deception_score}"
            f" | Status: {score.calculation_status}"
        )

    assert len(scores) == len(candidates)

    # Candidate analysis should not advance the model
    assert counter.ply == 2

    print("\nMulti-turn DREAD test completed!")


    # ----------------------------------------
    # Verify candidate independence
    # ----------------------------------------

    print("\nTesting candidate independence...")

    original_ply = counter.ply

    # Evaluate candidates in their original order
    first_results = counter.evaluate_candidates(
        candidates,
        ply=2
    )

    # Evaluate candidates in reverse order
    reversed_results = counter.evaluate_candidates(
        list(reversed(candidates)),
        ply=2
    )

    # Repeat the original evaluation
    repeated_results = counter.evaluate_candidates(
        candidates,
        ply=2
    )

    # Compare the actual uncertainty measurements
    first = {
        result.candidate_move: (
            result.calculation_status,
            result.scenario_measurements
        )
        for result in first_results
    }

    reversed_order = {
        result.candidate_move: (
            result.calculation_status,
            result.scenario_measurements
        )
        for result in reversed_results
    }

    repeated = {
        result.candidate_move: (
            result.calculation_status,
            result.scenario_measurements
        )
        for result in repeated_results
    }

    assert first == reversed_order
    assert first == repeated

    # Candidate evaluation must not advance the model
    assert counter.ply == original_ply

    # ----------------------------------------
    # Validate uncertainty measurements
    # ----------------------------------------

    print("\nValidating uncertainty measurements...")

    for result in first_results:

        print(f"\nCandidate: {result.candidate_move}")
        print(f"Status: {result.calculation_status}")
        print(f"Scenario count: {result.scenario_count}")

        if result.calculation_status == "estimated":

            assert result.scenario_count > 0

            for scenario in result.scenario_measurements:

                assert scenario.before > 0, (
                    "Invalid before count"
                )

                assert scenario.after > 0, (
                    "Invalid after count"
                )

            print("All scenario counts are positive.")

        else:
            print("No usable estimate:", result.reason)

    # Inspect the committed model's internal scenarios.
    # This private attribute is used only for testing.
    for i, scenario in enumerate(counter._scenarios, start=1):

        count = scenario.count_opponent_positions()

        print(f"Stored scenario {i}: {count} plausible boards")

        assert count > 0, (
            f"Stored scenario {i} has no plausible boards"
        )

    print("\nUncertainty validation passed!")

    print("Candidate order independence: PASSED")
    print("Repeated evaluation consistency: PASSED")
    print("Model ply unchanged: PASSED")

def inspect_black_visibility(actual_board, candidates):

    print("\nInspecting Black's possible visibility...")

    for move in candidates:

        simulated_board = actual_board.copy()
        simulated_board.push(move)

        black_observation = observe_board(
            simulated_board,
            chess.BLACK
        )

        print(f"\nCandidate: {move.uci()}")

        print(
            "Visible squares:",
            chess.popcount(black_observation.visible)
        )

        print(
            "Visible pieces:",
            black_observation.visible_pieces
        )

if __name__ == "__main__":
    test_multiturn()
