"""Immutable domain records shared across the simulator."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class PacketStatus(str, Enum):
    GENERATED = "generated"
    QUEUED = "queued"
    SELECTION_REQUESTED = "selection_requested"
    SELECTED = "selected"
    TRANSMISSION_STARTED = "transmission_started"
    DELIVERED_ON_TIME = "delivered_on_time"
    COLLIDED = "collided"
    EXPIRED_WHILE_QUEUED = "expired_while_queued"
    EXPIRED_WHILE_WAITING = "expired_while_waiting"
    NO_FEASIBLE_RESOURCE = "no_feasible_resource"


class TransmissionStatus(str, Enum):
    SCHEDULED = "scheduled"
    DELIVERED = "delivered"
    COLLIDED = "collided"


@dataclass(frozen=True)
class Packet:
    packet_id: int
    source_id: int
    destination_id: int
    generation_slot: int
    deadline_slot: int
    payload_size_bytes: int
    priority: int

    def __post_init__(self) -> None:
        if self.packet_id < 0:
            raise ValueError("packet_id must be non-negative")
        if self.source_id < 0 or self.destination_id < 0:
            raise ValueError("source_id and destination_id must be non-negative")
        if self.source_id == self.destination_id:
            raise ValueError("source_id and destination_id must differ")
        if self.generation_slot < 0:
            raise ValueError("generation_slot must be non-negative")
        if self.deadline_slot <= self.generation_slot:
            raise ValueError("deadline_slot must be after generation_slot")
        if self.payload_size_bytes <= 0:
            raise ValueError("payload_size_bytes must be positive")
        if self.priority <= 0:
            raise ValueError("priority must be positive")


@dataclass(frozen=True, order=True)
class Resource:
    slot: int
    start_subchannel: int
    width: int

    def __post_init__(self) -> None:
        if self.slot < 0:
            raise ValueError("slot must be non-negative")
        if self.start_subchannel < 0:
            raise ValueError("start_subchannel must be non-negative")
        if self.width <= 0:
            raise ValueError("width must be positive")

    @property
    def end_subchannel(self) -> int:
        """Return the exclusive end of this resource's subchannel interval."""
        return self.start_subchannel + self.width

    def overlaps(self, other: Resource) -> bool:
        return (
            self.slot == other.slot
            and self.start_subchannel < other.end_subchannel
            and other.start_subchannel < self.end_subchannel
        )


@dataclass(frozen=True)
class Transmission:
    packet: Packet
    resource: Resource
    status: TransmissionStatus = TransmissionStatus.SCHEDULED
    reservation_interval_slots: int | None = None


@dataclass(frozen=True)
class ResourceOffset:
    slot_offset: int
    start_subchannel: int
    width: int

    def __post_init__(self) -> None:
        if self.slot_offset < 0:
            raise ValueError("slot_offset must be non-negative")
        if self.start_subchannel < 0:
            raise ValueError("start_subchannel must be non-negative")
        if self.width <= 0:
            raise ValueError("width must be positive")


@dataclass(frozen=True)
class ReservationState:
    resource_offset: ResourceOffset
    reservation_interval_slots: int
    remaining_reselections: int
    keep_probability: float

    def __post_init__(self) -> None:
        if self.reservation_interval_slots <= 0:
            raise ValueError("reservation_interval_slots must be positive")
        if self.resource_offset.slot_offset >= self.reservation_interval_slots:
            raise ValueError("slot_offset must be smaller than reservation interval")
        if self.remaining_reselections <= 0:
            raise ValueError("remaining_reselections must be positive")
        if not 0.0 <= self.keep_probability <= 1.0:
            raise ValueError("keep_probability must be between 0 and 1")

    def next_resource_at_or_after(self, slot: int) -> Resource:
        if slot < 0:
            raise ValueError("slot must be non-negative")
        offset = self.resource_offset.slot_offset
        if slot <= offset:
            next_slot = offset
        else:
            distance = slot - offset
            periods = (distance + self.reservation_interval_slots - 1) // (
                self.reservation_interval_slots
            )
            next_slot = offset + periods * self.reservation_interval_slots
        return Resource(
            slot=next_slot,
            start_subchannel=self.resource_offset.start_subchannel,
            width=self.resource_offset.width,
        )


@dataclass(frozen=True)
class ReservationAdvance:
    state: ReservationState | None
    requires_reselection: bool


@dataclass(frozen=True)
class SelectionDecision:
    resource: Resource | None
    terminal_status: PacketStatus | None
    policy: str
    request_slot: int
    decision_slot: int
    initial_candidate_count: int
    excluded_candidate_count: int
    retained_candidate_count: int
    relaxation_level: int = 0
    reservation_state: ReservationState | None = None
    reservation_interval_slots: int | None = None


@dataclass(frozen=True)
class LifecycleRecord:
    packet_id: int
    node_id: int
    status: PacketStatus
    slot: int
    resource: Resource | None = None


@dataclass(frozen=True)
class SelectorDiagnostic:
    node_id: int
    packet_id: int
    policy: str
    request_slot: int
    decision_slot: int
    initial_candidate_count: int
    excluded_candidate_count: int
    retained_candidate_count: int
    relaxation_level: int
    selected_resource: Resource | None


@dataclass(frozen=True)
class SimulationResult:
    generated_packets: tuple[Packet, ...]
    transmissions: tuple[Transmission, ...]
    lifecycle_records: tuple[LifecycleRecord, ...]
    selector_diagnostics: tuple[SelectorDiagnostic, ...]
    generation_horizon_slot: int
    final_executed_slot: int
    num_subchannels: int
