import chess
from board_state_limiter import position_key

from fow_chess import FowBoard
from board_state_limiter import observe_board
from opponent_uncertainty_counter import (
    OpponentUncertaintyCounter,
    AssistedTurnEvent,
    _SearchBudget
)


def test_belief_consistency():

    actual_board = FowBoard()

    counter = OpponentUncertaintyCounter(
        assisted_color=chess.WHITE
    )

    # White plays e4
    white_move = chess.Move.from_uci("e2e4")
    actual_board.push(white_move)

    result = counter.update_model(
        AssistedTurnEvent(
            ply=1,
            own_move=white_move
        )
    )

    assert result.status == "applied"

    # Black plays e5
    actual_board.push_uci("e7e5")

    white_observation = observe_board(
        actual_board,
        chess.WHITE
    )

    result = counter.update_model(
        AssistedTurnEvent(
            ply=2,
            observation=white_observation
        )
    )

    assert result.status == "applied"

    candidates = [
        chess.Move.from_uci("g1f3"),
        chess.Move.from_uci("f1c4"),
        chess.Move.from_uci("d2d4")
    ]

    for move in candidates:

        print(f"\nTesting candidate: {move.uci()}")

        for parent in counter._scenarios:

            budget = _SearchBudget(
                max_positions=25000,
                timeout_seconds=None
            )

            children = tuple(
                counter._advance_scenario(
                    parent,
                    move,
                    budget
                )
            )

            for child in children:

                assert len(child.worlds) > 0

                assert len(child.opponent_boards) > 0, (
                    "No plausible opponent boards"
                )

                # Every world in this group should imply
                # the same observation for Black.
                world_observations = {
                    observe_board(board, chess.BLACK)
                    for board in child.worlds
                }

                assert len(world_observations) == 1

                expected_observation = next(
                    iter(world_observations)
                )

                # Every retained opponent belief board
                # should match that same Black observation.
                for board in child.opponent_boards:

                    belief_observation = observe_board(
                        board,
                        chess.BLACK
                    )

                    assert (
                        belief_observation
                        == expected_observation
                    ), (
                        f"Belief mismatch for {move.uci()}"
                    )

                # Count unique positions, excluding duplicates
                unique_positions = {
                    position_key(board)
                    for board in child.opponent_boards
                }

                print(
                    f"Candidate: {move.uci()} | "
                    f"Stored boards: {len(child.opponent_boards)} | "
                    f"Unique positions: {len(unique_positions)}"
                )

                # Verify the counter's deduplication logic
                assert (
                    len(unique_positions)
                    == child.count_opponent_positions()
                )


    print("\nBelief consistency test passed!")


if __name__ == "__main__":
    test_belief_consistency()
