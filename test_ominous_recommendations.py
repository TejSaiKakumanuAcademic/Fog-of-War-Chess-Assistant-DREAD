from unittest.mock import MagicMock, patch
import chess
import chess.engine

from fow_engine import FowEngine
from fow_chess import FowBoard


def test_ominous_recommendations():

    board = FowBoard()

    # Create FowEngine without opening a real engine
    fow_engine = FowEngine.__new__(FowEngine)

    fow_engine.board = board
    fow_engine.logger = MagicMock()
    fow_engine.settings = MagicMock()
    fow_engine.settings.search_depth = 5

    # Mock bias scoring without changing strategic scores
    fow_engine.bias_scorer = MagicMock()
    fow_engine.bias_scorer.get_before_vision_score.return_value = 0
    fow_engine.bias_scorer.move_bias_applicator.side_effect = (
        lambda move, score, board, vision: score
    )

    # Fake Fairy-Stockfish result
    fake_engine = MagicMock()

    fake_engine.analyse.return_value = [
        {
            "pv": [chess.Move.from_uci("e2e4")],
            "score": chess.engine.PovScore(
                chess.engine.Cp(100), chess.WHITE
            )
        },
        {
            "pv": [chess.Move.from_uci("g1f3")],
            "score": chess.engine.PovScore(
                chess.engine.Cp(80), chess.WHITE
            )
        }
    ]

    fow_engine.engine = fake_engine

    # Mock BSL with one possible board
    bsl = MagicMock()
    bsl.board_states = [board]

    # Mock PSA with one ranked board
    psa = MagicMock()
    psa.board_scores = [(0, 1.0)]

    # Avoid the regression calculation, which needs
    # multiple candidate scores and at least 2 points
    max_guesses = 3

    # Test DREAD mode: no popup
    with patch.object(
        fow_engine, "suggestion_message"
    ) as popup:

        results = fow_engine.suggest_player_move(
            bsl,
            psa,
            max_guesses=max_guesses,
            show_message=False
        )

        popup.assert_not_called()

    assert len(results) == 2
    assert results[0][0] == chess.Move.from_uci("e2e4")
    assert results[0][1] == 100
    assert results[1][0] == chess.Move.from_uci("g1f3")
    assert results[1][1] == 80

    print("DREAD mode: recommendations returned without popup.")

    # Test original behavior: popup appears
    with patch.object(
        fow_engine, "suggestion_message"
    ) as popup:

        results = fow_engine.suggest_player_move(
            bsl,
            psa,
            max_guesses=max_guesses
        )

        popup.assert_called_once()

    assert len(results) == 2

    print("Normal OMINOUS mode: popup behavior preserved.")
    print("OMINOUS recommendation interface test passed!")


if __name__ == "__main__":
    test_ominous_recommendations()
