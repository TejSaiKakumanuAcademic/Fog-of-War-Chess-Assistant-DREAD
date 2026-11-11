from dataclasses import replace
import unittest
from unittest.mock import patch

import chess

from board_state_limiter import observe_board, position_key
from fow_chess import FowBoard
from opponent_uncertainty_counter import (
    AssistedTurnEvent,
    OpponentUncertaintyCounter,
    _SearchBudget,
    _successors,
)


def played_event(
    board: FowBoard,
    uci: str,
    assisted_color: chess.Color,
    *,
    show_mover_view: bool = False,
    captured_piece: chess.Piece | None = None,
) -> AssistedTurnEvent:
    move = board.parse_uci(uci)
    own_move = move if board.turn == assisted_color else None
    board.push(move)
    outcome = board.outcome()
    observation = None
    if outcome is None and (board.turn == assisted_color or show_mover_view):
        observation = observe_board(board, assisted_color)
    return AssistedTurnEvent(board.ply(), own_move, observation, show_mover_view, captured_piece, outcome)


class BoardObservationTests(unittest.TestCase):
    def test_out_of_turn_view_preserves_board_and_clears_en_passant(self):
        board = FowBoard("4r1k1/8/8/3pP3/8/8/8/4K3 w - d6 0 2")
        original_fen = board.fen(en_passant="fen")

        self.assertEqual(observe_board(board, chess.WHITE).en_passant_visible, chess.BB_D5)
        self.assertEqual(observe_board(board, chess.BLACK).en_passant_visible, chess.BB_EMPTY)
        self.assertEqual(board.fen(en_passant="fen"), original_fen)
        self.assertEqual(board.move_stack, [])

    def test_semi_visible_blocker_reveals_occupancy_without_piece_type(self):
        board = FowBoard("7k/8/8/4n3/4P3/8/8/K7 w - - 0 1")
        observation = observe_board(board, chess.WHITE)
        board.set_piece_at(chess.E5, chess.Piece(chess.BISHOP, chess.BLACK))

        self.assertTrue(observation.semi_occupied & chess.BB_E5)
        self.assertFalse(observation.visible & chess.BB_E5)
        self.assertEqual(observe_board(board, chess.WHITE), observation)

    def test_position_key_uses_fog_legal_en_passant_and_castling_rights(self):
        board = FowBoard("4r1k1/8/8/3pP3/8/8/8/4K3 w - d6 0 2")
        self.assertFalse(board.has_legal_en_passant())
        self.assertIn(chess.Move.from_uci("e5d6"), board.fow_legal_moves)
        without_en_passant = board.copy()
        without_en_passant.ep_square = None
        self.assertNotEqual(position_key(board), position_key(without_en_passant))

        start = FowBoard()
        without_castling = start.copy()
        without_castling.castling_rights = chess.BB_EMPTY
        self.assertNotEqual(position_key(start), position_key(without_castling))

    def test_successor_keeps_repetition_history_without_counting_it_in_position_key(self):
        board = FowBoard()
        sequence = ["g1f3", "g8f6", "f3g1", "f6g8"]
        for uci in sequence + sequence[:3]:
            board.push_uci(uci)
        move = chess.Move.from_uci(sequence[-1])

        successor, = _successors((board,), _SearchBudget(1, None), (move,))

        self.assertEqual(successor.board.outcome(), chess.Outcome(chess.Termination.THREEFOLD_REPETITION, None))
        self.assertIsNone(successor.displayed_view(chess.WHITE, True))
        self.assertEqual(position_key(successor.board), position_key(FowBoard()))
        self.assertEqual(len(board.move_stack), 7)


class OpponentModelTests(unittest.TestCase):
    def test_opponent_mover_view_only_filters_beliefs_when_displayed(self):
        for show_mover_view, expected in [(False, 20), (True, 1)]:
            with self.subTest(show_mover_view=show_mover_view):
                counter = OpponentUncertaintyCounter(chess.WHITE)
                board = FowBoard()
                opening = played_event(board, "e2e4", chess.WHITE)
                reply = played_event(board, "g8f6", chess.WHITE, show_mover_view=show_mover_view)

                self.assertEqual(counter.update_model(opening).status, "applied")
                self.assertEqual(counter.update_model(reply).status, "applied")

                scenario, = [s for s in counter._scenarios if s.worlds[0].peek().uci() == "g8f6"]
                self.assertEqual(len({position_key(board) for board in scenario.opponent_boards}), expected)

    def test_new_assisted_observation_eliminates_old_hypotheses_with_black_assisted(self):
        counter = OpponentUncertaintyCounter(chess.BLACK)
        board = FowBoard()
        opening = played_event(board, "e2e4", chess.BLACK)
        reply = played_event(board, "g8f6", chess.BLACK, show_mover_view=True)

        self.assertIsNone(opening.own_move)
        self.assertEqual(counter.update_model(opening).status, "applied")
        self.assertEqual(len(counter._scenarios), 20)
        self.assertEqual(counter.update_model(reply).status, "applied")

        scenario, = counter._scenarios
        world, = scenario.worlds
        self.assertEqual([move.uci() for move in world.move_stack], ["e2e4", "g8f6"])
        self.assertEqual(len(scenario.opponent_boards), 13)

    def test_capture_and_en_passant_require_public_capture_fact(self):
        sequences = [
            ["e2e4", "d7d5", "e4d5"],
            ["e2e4", "a7a6", "e4e5", "d7d5", "e5d6"],
        ]
        for sequence in sequences:
            with self.subTest(capture=sequence[-1]):
                counter = OpponentUncertaintyCounter(chess.WHITE)
                board = FowBoard()
                for uci in sequence[:-1]:
                    self.assertEqual(counter.update_model(played_event(board, uci, chess.WHITE)).status, "applied")
                event = played_event(board, sequence[-1], chess.WHITE)

                self.assertEqual(counter.update_model(event).reason, "contradictory_event")
                self.assertEqual(counter.ply, len(sequence) - 1)
                event = replace(event, captured_piece=chess.Piece(chess.PAWN, chess.BLACK))
                self.assertEqual(counter.update_model(event).status, "applied")

    def test_interrupted_update_can_be_retried_at_same_ply(self):
        counter = OpponentUncertaintyCounter(chess.WHITE, max_positions=1)
        opening = played_event(FowBoard(), "e2e4", chess.WHITE)
        baseline = counter._scenarios

        result = counter.update_model(opening)
        self.assertEqual((result.status, result.ply, result.reason), ("incomplete", 0, "position_limit"))
        with patch("opponent_uncertainty_counter.monotonic", side_effect=[0, 2]):
            result = counter.update_model(opening, timeout_seconds=1)
        self.assertEqual((result.status, result.ply, result.reason), ("incomplete", 0, "time_limit"))
        self.assertIs(counter._scenarios, baseline)

        result = counter.update_model(opening, max_positions=21)
        self.assertEqual((result.status, result.ply, result.states_explored), ("applied", 1, 21))
        self.assertEqual(counter.update_model(opening).reason, "unexpected_ply")

    def test_out_of_scope_move_and_view_are_rejected(self):
        counter = OpponentUncertaintyCounter(chess.BLACK)
        board = FowBoard()
        event = played_event(board, "e2e4", chess.BLACK)

        self.assertEqual(counter.update_model(replace(event, own_move=board.peek())).reason, "unexpected_move")
        self.assertEqual(counter.update_model(replace(event, observation=None)).reason, "unexpected_observation")
        wrong_view = replace(event, observation=observe_board(board, chess.WHITE))
        self.assertEqual(counter.update_model(wrong_view).reason, "unexpected_observer")
        self.assertEqual(counter.ply, 0)
