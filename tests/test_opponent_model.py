from dataclasses import replace
import unittest
from unittest.mock import patch

import chess

from board_state_limiter import observe_board, position_key
from fow_chess import FowBoard
from opponent_uncertainty_counter import (
    AssistedTurnEvent,
    OpponentUncertaintyCounter,
    ScenarioMeasurement,
    _Scenario,
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


class CandidateEvaluationTests(unittest.TestCase):
    def opening_model(self) -> OpponentUncertaintyCounter:
        board = FowBoard()
        counter = OpponentUncertaintyCounter(chess.WHITE)
        for uci in ("e2e4", "g8f6"):
            self.assertEqual(counter.update_model(played_event(board, uci, chess.WHITE)).status, "applied")
        return counter

    def test_reference_opening_counts(self):
        start = OpponentUncertaintyCounter(chess.WHITE)
        result = start.evaluate_candidate(chess.Move.from_uci("e2e4"), ply=0)
        self.assertEqual(result.calculation_status, "estimated")
        self.assertEqual(result.scenario_measurements, (ScenarioMeasurement(1, 20),))

        counter = self.opening_model()
        moves = [chess.Move.from_uci(uci) for uci in ("g1f3", "e4e5")]
        knight, pawn = counter.evaluate_candidates(moves, ply=2)
        self.assertEqual((knight.candidate_move, pawn.candidate_move), ("g1f3", "e4e5"))
        self.assertEqual(knight.calculation_status, "estimated")
        self.assertEqual(pawn.calculation_status, "estimated")
        self.assertEqual((knight.scenario_count, knight.min_states, knight.max_states), (13, 25, 246))
        self.assertCountEqual(knight.scenario_measurements, (
            ScenarioMeasurement(20, after)
            for after in [25, 170, 176, 181, 187, 200, 202, 226] + [246] * 5
        ))
        self.assertCountEqual(pawn.scenario_measurements, (
            [ScenarioMeasurement(20, 1)] * 3 + [ScenarioMeasurement(20, 2)] * 10
        ))
        self.assertAlmostEqual(pawn.average_states, 23 / 13)

    def test_candidate_order_and_repetition_leave_baseline_unchanged(self):
        counter = self.opening_model()
        moves = [chess.Move.from_uci(uci) for uci in ("g1f3", "e4e5")]
        baseline = counter._scenarios
        boards = [board for scenario in baseline for board in (*scenario.worlds, *scenario.opponent_boards)]
        positions = [(board.fen(en_passant="fen"), tuple(board.move_stack)) for board in boards]

        first = counter.evaluate_candidates(moves, ply=2)
        reverse = counter.evaluate_candidates(reversed(moves), ply=2)
        repeated = counter.evaluate_candidate(moves[0], ply=2)

        for left, right in zip(first, reversed(reverse)):
            self.assertEqual(replace(left, processing_time_seconds=0), replace(right, processing_time_seconds=0))
        self.assertEqual(replace(first[0], processing_time_seconds=0), replace(repeated, processing_time_seconds=0))
        self.assertIs(counter._scenarios, baseline)
        self.assertEqual(counter.ply, 2)
        self.assertEqual([(board.fen(en_passant="fen"), tuple(board.move_stack)) for board in boards], positions)

    def test_same_visible_events_give_same_results_for_different_hidden_replies(self):
        move = chess.Move.from_uci("g1f3")
        replies, positions, results = [], [], []
        for uci in ("g8f6", "c7c5"):
            board = FowBoard()
            counter = OpponentUncertaintyCounter(chess.WHITE)
            self.assertEqual(counter.update_model(played_event(board, "e2e4", chess.WHITE)).status, "applied")
            reply = played_event(board, uci, chess.WHITE)
            replies.append(reply)
            positions.append(position_key(board))
            self.assertEqual(counter.update_model(reply).status, "applied")
            result = counter.evaluate_candidate(move, ply=2)
            results.append(replace(result, processing_time_seconds=0))

        self.assertNotEqual(*positions)
        self.assertEqual(*replies)
        self.assertEqual(*results)

    def test_black_candidates_are_available_after_white_plays(self):
        counter = OpponentUncertaintyCounter(chess.BLACK)
        move = chess.Move.from_uci("g8f6")
        self.assertEqual(counter.evaluate_candidate(move, ply=0).reason, "opponent_to_move")
        opening = played_event(FowBoard(), "e2e4", chess.BLACK)
        self.assertEqual(counter.update_model(opening).status, "applied")

        result = counter.evaluate_candidate(move, ply=1)

        self.assertEqual(result.calculation_status, "estimated")
        self.assertEqual((result.scenario_count, result.min_states, result.max_states), (20, 13, 20))

    def test_transpositions_count_once_per_scenario_and_survive_in_distinct_histories(self):
        first, same_observations, different_opponent_moves = FowBoard(), FowBoard(), FowBoard()
        for board, moves in [
            (first, ["e2e3", "e7e6", "d2d3", "d7d6"]),
            (same_observations, ["d2d3", "e7e6", "e2e3", "d7d6"]),
            (different_opponent_moves, ["e2e3", "d7d6", "d2d3", "e7e6"]),
        ]:
            for uci in moves:
                board.push_uci(uci)
        counter = OpponentUncertaintyCounter(chess.WHITE)
        counter._ply = 4
        counter._scenarios = (
            _Scenario((first,), (first, same_observations)),
            _Scenario((different_opponent_moves,), (different_opponent_moves,)),
        )

        result = counter.evaluate_candidate(chess.Move.from_uci("g1f3"), ply=4)

        self.assertEqual(result.scenario_count, 2)
        self.assertEqual(result.scenario_measurements[0], result.scenario_measurements[1])
        self.assertEqual(result.scenario_measurements[0].before, 1)

    def test_limits_drop_partial_counts_and_stale_or_illegal_candidates_are_invalid(self):
        counter = self.opening_model()
        move = chess.Move.from_uci("g1f3")
        capped = counter.evaluate_candidate(move, ply=2, max_positions=600)
        with patch("opponent_uncertainty_counter.monotonic", side_effect=[0, 2, 2]):
            expired = counter.evaluate_candidate(move, ply=2, timeout_seconds=1)
        stale = counter.evaluate_candidate(move, ply=1)
        illegal = counter.evaluate_candidate(chess.Move.from_uci("e2e4"), ply=2)

        for result, status, reason in [
            (capped, "incomplete", "position_limit"), (expired, "incomplete", "time_limit"),
            (stale, "invalid", "unexpected_ply"), (illegal, "invalid", "illegal_candidate"),
        ]:
            with self.subTest(reason=reason):
                self.assertEqual((result.calculation_status, result.reason), (status, reason))
                self.assertEqual(result.scenario_measurements, ())
                self.assertIsNone(result.min_states)
                self.assertIsNone(result.max_states)
                self.assertIsNone(result.average_states)
        self.assertEqual(capped.states_explored, 600)
        self.assertEqual(counter.evaluate_candidate(move, ply=2).calculation_status, "estimated")
