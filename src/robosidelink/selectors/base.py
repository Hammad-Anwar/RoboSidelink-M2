"""Shared resource-selector contract."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

from robosidelink.models import Packet, ReservationState, Resource, SelectionDecision

if TYPE_CHECKING:
    from robosidelink.observers.base import ObservationSnapshot


@dataclass(frozen=True)
class SelectionContext:
    node_id: int
    packet: Packet
    request_slot: int
    decision_slot: int
    candidates: tuple[Resource, ...]
    observation: ObservationSnapshot | None
    reservation_state: ReservationState | None = None


class ResourceSelector(Protocol):
    def select(self, context: SelectionContext) -> SelectionDecision:
        """Choose one supplied candidate or return a terminal decision."""
