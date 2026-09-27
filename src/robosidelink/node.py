"""Mutable per-robot queue state owned by the simulation engine."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field

from robosidelink.models import Packet, ReservationState
from robosidelink.selectors.base import ResourceSelector


@dataclass
class NodeState:
    node_id: int
    destination_id: int
    selector: ResourceSelector
    queue: deque[Packet] = field(default_factory=deque)
    active_packet: Packet | None = None
    reservation_state: ReservationState | None = None

    def enqueue(self, packet: Packet) -> None:
        self.queue.append(packet)

    def activate_head(self) -> Packet | None:
        if self.active_packet is not None or not self.queue:
            return None
        self.active_packet = self.queue.popleft()
        return self.active_packet

    def complete_active(self, packet_id: int) -> None:
        if self.active_packet is not None and self.active_packet.packet_id == packet_id:
            self.active_packet = None

    def expire_queued(self, boundary_slot: int) -> tuple[Packet, ...]:
        expired = tuple(
            packet for packet in self.queue if packet.deadline_slot <= boundary_slot
        )
        if expired:
            expired_ids = {packet.packet_id for packet in expired}
            self.queue = deque(
                packet for packet in self.queue if packet.packet_id not in expired_ids
            )
        return expired

    @property
    def idle(self) -> bool:
        return self.active_packet is None and not self.queue
