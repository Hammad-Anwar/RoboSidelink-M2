"""Deterministic integer-slot simulation engine."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Mapping

from robosidelink.channel import DeterministicCollisionChannel
from robosidelink.config import RunConfig
from robosidelink.models import (
    LifecycleRecord,
    Packet,
    PacketStatus,
    SelectionDecision,
    SelectorDiagnostic,
    SimulationResult,
    Transmission,
    TransmissionStatus,
)
from robosidelink.node import NodeState
from robosidelink.observers.history import HistoryObserver
from robosidelink.randomness import NamedRandomStreams
from robosidelink.resource_pool import ResourcePool
from robosidelink.selectors.base import ResourceSelector, SelectionContext
from robosidelink.selectors.random_selector import RandomSelector
from robosidelink.selectors.mode2 import Rel16Mode2InspiredSelector
from robosidelink.traffic import (
    JitteredPeriodicTrafficGenerator,
    PeriodicTrafficGenerator,
)


@dataclass(frozen=True)
class _PendingSelection:
    node_id: int
    packet: Packet
    request_slot: int
    decision_slot: int


class SimulationEngine:
    def __init__(
        self,
        config: RunConfig,
        *,
        selectors: Mapping[int, ResourceSelector] | None = None,
    ) -> None:
        self.config = config
        self._streams = NamedRandomStreams(config.simulation.seed)
        self._pool = ResourcePool(config.radio.num_subchannels)
        self._channel = DeterministicCollisionChannel()
        self._observers = {
            node_id: HistoryObserver(config.selector.mode2.sensing_window_slots)
            for node_id in range(config.scenario.num_robots)
        }

        supplied = dict(selectors or {})
        self._nodes: dict[int, NodeState] = {}
        for node_id in range(config.scenario.num_robots):
            destination_id = node_id + 1 if node_id % 2 == 0 else node_id - 1
            selector = supplied.get(node_id)
            if selector is None:
                if config.selector.policy == "rel16-mode2-inspired":
                    selector = Rel16Mode2InspiredSelector(
                        config.selector.mode2,
                        choice_rng=self._streams.rng(f"selector:{node_id}"),
                        counter_rng=self._streams.rng(
                            f"reselection-counter:{node_id}"
                        ),
                        keep_rng=self._streams.rng(f"reservation-keep:{node_id}"),
                    )
                else:
                    selector = RandomSelector(
                        self._streams.rng(f"selector:{node_id}")
                    )
            self._nodes[node_id] = NodeState(
                node_id=node_id,
                destination_id=destination_id,
                selector=selector,
            )

        self._periodic = PeriodicTrafficGenerator(config.traffic.period_slots)
        self._jittered: dict[int, JitteredPeriodicTrafficGenerator] = {}
        self._next_jittered_arrival: dict[int, int] = {}
        if config.traffic.kind == "jittered-periodic":
            for node_id in self._nodes:
                self._jittered[node_id] = JitteredPeriodicTrafficGenerator(
                    config.traffic.period_slots,
                    config.traffic.jitter_slots,
                    self._streams.rng(f"traffic:{node_id}"),
                )
                self._next_jittered_arrival[node_id] = 0

    def run(self) -> SimulationResult:
        generated_packets: list[Packet] = []
        resolved_transmissions: list[Transmission] = []
        lifecycle_records: list[LifecycleRecord] = []
        selector_diagnostics: list[SelectorDiagnostic] = []
        scheduled: dict[int, list[Transmission]] = defaultdict(list)
        pending: dict[int, list[_PendingSelection]] = defaultdict(list)
        next_packet_id = 0
        slot = 0

        while True:
            if slot > 0:
                completed = self._channel.resolve(tuple(scheduled.pop(slot - 1, ())))
                resolved_transmissions.extend(completed)
                transmitting_nodes = {
                    transmission.packet.source_id for transmission in completed
                }
                for observer_node_id, observer in self._observers.items():
                    if observer_node_id in transmitting_nodes:
                        continue
                    for transmission in completed:
                        observer.record_activity(
                            transmission.resource,
                            observed_slot=slot - 1,
                            source_id=transmission.packet.source_id,
                            reservation_interval_slots=(
                                transmission.reservation_interval_slots
                            ),
                        )
                for transmission in completed:
                    terminal_status = (
                        PacketStatus.DELIVERED_ON_TIME
                        if transmission.status is TransmissionStatus.DELIVERED
                        else PacketStatus.COLLIDED
                    )
                    lifecycle_records.append(
                        LifecycleRecord(
                            packet_id=transmission.packet.packet_id,
                            node_id=transmission.packet.source_id,
                            status=terminal_status,
                            slot=slot,
                            resource=transmission.resource,
                        )
                    )
                    self._nodes[transmission.packet.source_id].complete_active(
                        transmission.packet.packet_id
                    )

            if slot < self.config.simulation.duration_slots:
                for node in self._nodes.values():
                    if self._arrives(node.node_id, slot):
                        packet = Packet(
                            packet_id=next_packet_id,
                            source_id=node.node_id,
                            destination_id=node.destination_id,
                            generation_slot=slot,
                            deadline_slot=slot + self.config.traffic.deadline_slots,
                            payload_size_bytes=self.config.traffic.packet_size_bytes,
                            priority=1,
                        )
                        next_packet_id += 1
                        generated_packets.append(packet)
                        node.enqueue(packet)
                        lifecycle_records.extend(
                            (
                                LifecycleRecord(
                                    packet.packet_id,
                                    node.node_id,
                                    PacketStatus.GENERATED,
                                    slot,
                                ),
                                LifecycleRecord(
                                    packet.packet_id,
                                    node.node_id,
                                    PacketStatus.QUEUED,
                                    slot,
                                ),
                            )
                        )

            self._expire_at_boundary(
                slot,
                scheduled,
                pending,
                lifecycle_records,
            )

            for item in pending.pop(slot, ()):
                self._complete_selection(
                    item,
                    scheduled,
                    lifecycle_records,
                    selector_diagnostics,
                )

            for node in self._nodes.values():
                packet = node.activate_head()
                if packet is None:
                    continue
                lifecycle_records.append(
                    LifecycleRecord(
                        packet.packet_id,
                        node.node_id,
                        PacketStatus.SELECTION_REQUESTED,
                        slot,
                    )
                )
                decision_slot = slot + self.config.selector.processing_delay_slots
                item = _PendingSelection(
                    node_id=node.node_id,
                    packet=packet,
                    request_slot=slot,
                    decision_slot=decision_slot,
                )
                if decision_slot == slot:
                    self._complete_selection(
                        item,
                        scheduled,
                        lifecycle_records,
                        selector_diagnostics,
                    )
                else:
                    pending[decision_slot].append(item)

            for transmission in scheduled.get(slot, ()):
                lifecycle_records.append(
                    LifecycleRecord(
                        transmission.packet.packet_id,
                        transmission.packet.source_id,
                        PacketStatus.TRANSMISSION_STARTED,
                        slot,
                        transmission.resource,
                    )
                )

            if slot >= self.config.simulation.duration_slots and self._drained(
                scheduled, pending
            ):
                break
            slot += 1

        return SimulationResult(
            generated_packets=tuple(generated_packets),
            transmissions=tuple(resolved_transmissions),
            lifecycle_records=tuple(lifecycle_records),
            selector_diagnostics=tuple(selector_diagnostics),
            generation_horizon_slot=self.config.simulation.duration_slots,
            final_executed_slot=slot,
            num_subchannels=self.config.radio.num_subchannels,
        )

    def _arrives(self, node_id: int, slot: int) -> bool:
        if self.config.traffic.kind == "periodic":
            return bool(self._periodic.arrivals_at(slot))
        if slot != self._next_jittered_arrival[node_id]:
            return False
        self._next_jittered_arrival[node_id] = self._jittered[node_id].next_arrival(
            slot
        )
        return True

    def _complete_selection(
        self,
        item: _PendingSelection,
        scheduled: dict[int, list[Transmission]],
        lifecycle_records: list[LifecycleRecord],
        selector_diagnostics: list[SelectorDiagnostic],
    ) -> None:
        node = self._nodes[item.node_id]
        start_slot = max(
            item.request_slot + self.config.selector.mode2.t1_slots,
            item.decision_slot,
        )
        end_slot = min(
            item.request_slot + self.config.selector.mode2.t2_slots,
            item.packet.deadline_slot - 1,
        )
        candidates = (
            self._pool.candidates(
                start_slot,
                end_slot,
                self.config.radio.resource_width_subchannels,
            )
            if start_slot <= end_slot
            else ()
        )
        context = SelectionContext(
            node_id=item.node_id,
            packet=item.packet,
            request_slot=item.request_slot,
            decision_slot=item.decision_slot,
            candidates=candidates,
            observation=self._observers[item.node_id].snapshot(
                decision_slot=item.decision_slot,
                candidate_resources=candidates,
            ),
            reservation_state=node.reservation_state,
        )
        decision: SelectionDecision = node.selector.select(context)
        node.reservation_state = decision.reservation_state
        selector_diagnostics.append(
            SelectorDiagnostic(
                node_id=item.node_id,
                packet_id=item.packet.packet_id,
                policy=decision.policy,
                request_slot=decision.request_slot,
                decision_slot=decision.decision_slot,
                initial_candidate_count=decision.initial_candidate_count,
                excluded_candidate_count=decision.excluded_candidate_count,
                retained_candidate_count=decision.retained_candidate_count,
                relaxation_level=decision.relaxation_level,
                selected_resource=decision.resource,
            )
        )
        if decision.resource is None:
            lifecycle_records.append(
                LifecycleRecord(
                    item.packet.packet_id,
                    item.node_id,
                    decision.terminal_status or PacketStatus.NO_FEASIBLE_RESOURCE,
                    item.decision_slot,
                )
            )
            node.complete_active(item.packet.packet_id)
            return
        lifecycle_records.append(
            LifecycleRecord(
                item.packet.packet_id,
                item.node_id,
                PacketStatus.SELECTED,
                item.decision_slot,
                decision.resource,
            )
        )
        scheduled[decision.resource.slot].append(
            Transmission(
                packet=item.packet,
                resource=decision.resource,
                reservation_interval_slots=decision.reservation_interval_slots,
            )
        )

    def _expire_at_boundary(
        self,
        slot: int,
        scheduled: dict[int, list[Transmission]],
        pending: dict[int, list[_PendingSelection]],
        lifecycle_records: list[LifecycleRecord],
    ) -> None:
        for node in self._nodes.values():
            for packet in node.expire_queued(slot):
                lifecycle_records.append(
                    LifecycleRecord(
                        packet.packet_id,
                        node.node_id,
                        PacketStatus.EXPIRED_WHILE_QUEUED,
                        slot,
                    )
                )

        for completion_slot in tuple(pending):
            retained: list[_PendingSelection] = []
            for item in pending[completion_slot]:
                if item.packet.deadline_slot <= slot:
                    lifecycle_records.append(
                        LifecycleRecord(
                            item.packet.packet_id,
                            item.node_id,
                            PacketStatus.NO_FEASIBLE_RESOURCE,
                            slot,
                        )
                    )
                    self._nodes[item.node_id].complete_active(item.packet.packet_id)
                else:
                    retained.append(item)
            if retained:
                pending[completion_slot] = retained
            else:
                pending.pop(completion_slot, None)

        for resource_slot in tuple(scheduled):
            retained_transmissions: list[Transmission] = []
            for transmission in scheduled[resource_slot]:
                if transmission.packet.deadline_slot <= slot:
                    lifecycle_records.append(
                        LifecycleRecord(
                            transmission.packet.packet_id,
                            transmission.packet.source_id,
                            PacketStatus.EXPIRED_WHILE_WAITING,
                            slot,
                            transmission.resource,
                        )
                    )
                    self._nodes[
                        transmission.packet.source_id
                    ].complete_active(transmission.packet.packet_id)
                else:
                    retained_transmissions.append(transmission)
            if retained_transmissions:
                scheduled[resource_slot] = retained_transmissions
            else:
                scheduled.pop(resource_slot, None)

    def _drained(
        self,
        scheduled: Mapping[int, list[Transmission]],
        pending: Mapping[int, list[_PendingSelection]],
    ) -> bool:
        return (
            not any(scheduled.values())
            and not any(pending.values())
            and all(node.idle for node in self._nodes.values())
        )

    def observer_for(self, node_id: int) -> HistoryObserver:
        """Expose a node observer for diagnostics and controlled experiments."""
        return self._observers[node_id]
