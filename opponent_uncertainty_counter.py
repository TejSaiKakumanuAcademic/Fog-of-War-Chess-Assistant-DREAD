from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from math import isfinite
from time import monotonic
from typing import Literal

import chess

from board_state_limiter import BoardObservation, observe_board
from fow_chess import FowBoard


@dataclass(frozen=True)
class AssistedTurnEvent:
    """The facts available to the assisted player after one played move."""

    ply: int
    own_move: chess.Move | None = None
    observation: BoardObservation | None = None
    show_mover_view: bool = False
    captured_piece: chess.Piece | None = None
    outcome: chess.Outcome | None = None


@dataclass(frozen=True)
class ModelUpdateResult:
    status: Literal["applied", "incomplete", "invalid"]
    ply: int
    states_explored: int = 0
    reason: str | None = None


@dataclass(frozen=True)
class _MoveFacts:
    captured_symbol: str | None
    outcome: tuple[chess.Termination, chess.Color | None] | None

    @classmethod
    def from_observed(
        cls, captured_piece: chess.Piece | None, outcome: chess.Outcome | None,
    ) -> _MoveFacts:
        return cls(
            captured_piece.symbol() if captured_piece else None,
            (outcome.termination, outcome.winner) if outcome else None,
        )


@dataclass(frozen=True)
class _OpponentObservation:
    own_move: chess.Move | None
    view: BoardObservation | None
    facts: _MoveFacts


@dataclass(frozen=True)
class _Successor:
    board: FowBoard
    move: chess.Move
    facts: _MoveFacts

    def displayed_view(self, viewer: chess.Color, show_mover_view: bool) -> BoardObservation | None:
        if self.facts.outcome is None and (self.board.turn == viewer or show_mover_view):
            return observe_board(self.board, viewer)
        return None

    def opponent_observation(self, color: chess.Color, show_mover_view: bool) -> _OpponentObservation:
        own_move = self.move if self.board.turn != color else None
        return _OpponentObservation(own_move, self.displayed_view(color, show_mover_view), self.facts)


@dataclass(frozen=True)
class _Scenario:
    worlds: tuple[FowBoard, ...]
    opponent_boards: tuple[FowBoard, ...]


class _SearchLimit(Exception):
    pass


class _SearchBudget:
    def __init__(self, max_positions: int, timeout_seconds: float | None):
        if max_positions < 1:
            raise ValueError("max_positions must be positive")
        if timeout_seconds is not None and (not isfinite(timeout_seconds) or timeout_seconds <= 0):
            raise ValueError("timeout_seconds must be finite and positive")
        self.max_positions = max_positions
        self.started_at = monotonic()
        self.deadline = self.started_at + timeout_seconds if timeout_seconds is not None else None
        self.states_explored = 0

    def check_time(self) -> None:
        if self.deadline is not None and monotonic() >= self.deadline:
            raise _SearchLimit("time_limit")

    def visit(self) -> None:
        self.check_time()
        if self.states_explored >= self.max_positions:
            raise _SearchLimit("position_limit")
        self.states_explored += 1


def _successors(
    boards: tuple[FowBoard, ...], budget: _SearchBudget, moves: tuple[chess.Move, ...] | None,
) -> Iterator[_Successor]:
    for board in boards:
        budget.check_time()
        legal_moves = board.fow_legal_moves
        moves_to_try = legal_moves if moves is None else (move for move in moves if move in legal_moves)
        for move in moves_to_try:
            budget.visit()
            capture_square = move.to_square
            if board.is_en_passant(move):
                capture_square = chess.square(
                    chess.square_file(move.to_square), chess.square_rank(move.from_square),
                )
            captured_piece = board.piece_at(capture_square)
            child = board.copy()
            child.push(move)
            yield _Successor(child, move, _MoveFacts.from_observed(captured_piece, child.outcome()))


class OpponentUncertaintyCounter:
    """Track what an opponent could know using only assisted-player evidence."""

    def __init__(
        self,
        assisted_color: chess.Color,
        *,
        max_positions: int = 25_000,
        timeout_seconds: float | None = None,
    ):
        self._assisted_color = assisted_color
        self._max_positions = max_positions
        self._timeout_seconds = timeout_seconds
        start = FowBoard()
        self._scenarios = (_Scenario((start,), (start,)),)
        self._ply = 0
        self._game_over = False

    @property
    def ply(self) -> int:
        return self._ply

    def _search_budget(self, max_positions: int | None, timeout_seconds: float | None) -> _SearchBudget:
        return _SearchBudget(
            self._max_positions if max_positions is None else max_positions,
            self._timeout_seconds if timeout_seconds is None else timeout_seconds,
        )

    def _assisted_to_move(self) -> bool:
        turn = chess.WHITE if self._ply % 2 == 0 else chess.BLACK
        return turn == self._assisted_color

    def update_model(
        self,
        event: AssistedTurnEvent,
        *,
        max_positions: int | None = None,
        timeout_seconds: float | None = None,
    ) -> ModelUpdateResult:
        """Commit an event only after the full ply has been reconstructed."""
        invalid_reason = self._validate_event(event)
        if invalid_reason:
            return ModelUpdateResult("invalid", self.ply, reason=invalid_reason)

        budget = self._search_budget(max_positions, timeout_seconds)
        try:
            scenarios = tuple(
                child
                for parent in self._scenarios
                for child in self._advance_scenario(parent, event.own_move, event.show_mover_view, budget, event)
            )
            budget.check_time()
        except _SearchLimit as error:
            return ModelUpdateResult("incomplete", self.ply, budget.states_explored, str(error))

        if not scenarios:
            return ModelUpdateResult("invalid", self.ply, budget.states_explored, "contradictory_event")
        self._scenarios = scenarios
        self._ply = event.ply
        self._game_over = event.outcome is not None
        return ModelUpdateResult("applied", self.ply, budget.states_explored)

    def _validate_event(self, event: AssistedTurnEvent) -> str | None:
        if self._game_over:
            return "game_over"
        if event.ply != self.ply + 1:
            return "unexpected_ply"
        assisted_moved = self._assisted_to_move()
        if (event.own_move is not None) != assisted_moved:
            return "unexpected_move"
        has_view = event.outcome is None and (not assisted_moved or event.show_mover_view)
        if (event.observation is not None) != has_view:
            return "unexpected_observation"
        if event.observation is not None and event.observation.observer != self._assisted_color:
            return "unexpected_observer"
        return None

    def _advance_scenario(
        self,
        scenario: _Scenario,
        assisted_move: chess.Move | None,
        show_mover_view: bool,
        budget: _SearchBudget,
        event: AssistedTurnEvent | None = None,
    ) -> Iterator[_Scenario]:
        opponent = not self._assisted_color
        world_moves = (assisted_move,) if assisted_move is not None else None
        observed_facts = _MoveFacts.from_observed(event.captured_piece, event.outcome) if event else None
        worlds_by_observation: dict[_OpponentObservation, list[FowBoard]] = {}
        for successor in _successors(scenario.worlds, budget, world_moves):
            if event is not None:
                if successor.facts != observed_facts:
                    continue
                if successor.displayed_view(self._assisted_color, show_mover_view) != event.observation:
                    continue
            observation = successor.opponent_observation(opponent, show_mover_view)
            worlds_by_observation.setdefault(observation, []).append(successor.board)

        if not worlds_by_observation:
            return
        opponent_moves = None
        if assisted_move is None:
            opponent_moves = tuple(dict.fromkeys(
                observation.own_move
                for observation in worlds_by_observation
                if observation.own_move is not None
            ))

        # Only the worlds are constrained by the assisted player's evidence.
        beliefs_by_observation = {observation: [] for observation in worlds_by_observation}
        for successor in _successors(scenario.opponent_boards, budget, opponent_moves):
            observation = successor.opponent_observation(opponent, show_mover_view)
            if observation in beliefs_by_observation:
                beliefs_by_observation[observation].append(successor.board)

        for observation, worlds in worlds_by_observation.items():
            yield _Scenario(tuple(worlds), tuple(beliefs_by_observation[observation]))
