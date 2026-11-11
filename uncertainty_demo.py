import chess

from board_state_limiter import observe_board
from fow_chess import FowBoard
from opponent_uncertainty_counter import AssistedTurnEvent, OpponentUncertaintyCounter, UncertaintyResult


def print_result(result: UncertaintyResult) -> None:
    print(f"{result.candidate_move} [{result.calculation_status}]")
    if result.scenario_measurements:
        pairs = ", ".join(f"{pair.before} -> {pair.after}" for pair in result.scenario_measurements)
        print(f"  Before -> after per scenario ({result.scenario_count} total): {pairs}")
        print(f"  After counts: {result.min_states}–{result.max_states}, mean {result.average_states:.2f}")
    elif result.reason:
        print(f"  {result.reason}")
    print(f"  Examined {result.states_explored} successors in {result.processing_time_seconds:.3f} s")


def main() -> None:
    counter = OpponentUncertaintyCounter(chess.WHITE)
    opening = chess.Move.from_uci("e2e4")
    print("White assisted, Player Transition off")
    print_result(counter.evaluate_candidate(opening, ply=0))

    # The fixture board supplies White's displayed view after Black's reply.
    fixture = FowBoard()
    fixture.push(opening)
    fixture.push_uci("g8f6")
    for event in (
        AssistedTurnEvent(ply=1, own_move=opening),
        AssistedTurnEvent(ply=2, observation=observe_board(fixture, chess.WHITE)),
    ):
        update = counter.update_model(event)
        if update.status != "applied":
            raise RuntimeError(f"Could not apply ply {event.ply}: {update.reason}")

    print("\nWhite's next candidates after replaying 1. e4 Nf6")
    moves = [chess.Move.from_uci(uci) for uci in ("g1f3", "e4e5")]
    for result in counter.evaluate_candidates(moves, ply=2):
        print_result(result)


if __name__ == "__main__":
    main()
