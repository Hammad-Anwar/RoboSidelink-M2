from dataclasses import replace
from pathlib import Path

from robosidelink.config import load_config
from robosidelink.engine import SimulationEngine
from robosidelink.models import Packet, PacketStatus, Resource, SelectionDecision
from robosidelink.node import NodeState
from robosidelink.selectors.base import SelectionContext


class CapturingFirstSelector:
    policy_name = "capture-first"

    def __init__(self) -> None:
        self.contexts: list[SelectionContext] = []

    def select(self, context: SelectionContext) -> SelectionDecision:
        self.contexts.append(context)
        resource = context.candidates[0] if context.candidates else None
        return SelectionDecision(
            resource=resource,
            terminal_status=(
                None if resource else PacketStatus.NO_FEASIBLE_RESOURCE
            ),
            policy=self.policy_name,
            request_slot=context.request_slot,
            decision_slot=context.decision_slot,
            initial_candidate_count=len(context.candidates),
            excluded_candidate_count=0,
            retained_candidate_count=len(context.candidates),
        )


class AfterDeadlineSelector:
    policy_name = "after-deadline-test"

    def select(self, context: SelectionContext) -> SelectionDecision:
        resource = Resource(
            slot=context.packet.deadline_slot,
            start_subchannel=0,
            width=1,
        )
        return SelectionDecision(
            resource=resource,
            terminal_status=None,
            policy=self.policy_name,
            request_slot=context.request_slot,
            decision_slot=context.decision_slot,
            initial_candidate_count=len(context.candidates),
            excluded_candidate_count=0,
            retained_candidate_count=len(context.candidates),
        )


def _config(deadline_slots: int = 4):
    config = load_config(Path("configs/quickstart.yaml"))
    return replace(
        config,
        simulation=replace(config.simulation, duration_slots=1),
        traffic=replace(config.traffic, deadline_slots=deadline_slots),
        selector=replace(
            config.selector,
            mode2=replace(config.selector.mode2, t1_slots=0, t2_slots=8),
        ),
    )


def test_candidate_may_complete_exactly_at_deadline_not_one_slot_later() -> None:
    first = CapturingFirstSelector()
    second = CapturingFirstSelector()
    config = _config(deadline_slots=4)

    SimulationEngine(config, selectors={0: first, 1: second}).run()

    candidates = first.contexts[0].candidates
    assert max(resource.slot for resource in candidates) == 3
    assert all(resource.slot != 4 for resource in candidates)


def test_node_reports_packets_that_expire_while_queued() -> None:
    node = NodeState(node_id=0, destination_id=1, selector=CapturingFirstSelector())
    node.enqueue(Packet(0, 0, 1, 0, 3, 64, 1))
    node.enqueue(Packet(1, 0, 1, 0, 1, 64, 1))

    expired = node.expire_queued(boundary_slot=1)

    assert [packet.packet_id for packet in expired] == [1]
    assert [packet.packet_id for packet in node.queue] == [0]


def test_engine_reports_no_feasible_resource() -> None:
    config = _config(deadline_slots=4)
    config = replace(
        config,
        selector=replace(
            config.selector,
            mode2=replace(config.selector.mode2, t1_slots=5, t2_slots=6),
        ),
    )

    result = SimulationEngine(config).run()

    terminal = [
        record.status
        for record in result.lifecycle_records
        if record.status is PacketStatus.NO_FEASIBLE_RESOURCE
    ]
    assert terminal == [
        PacketStatus.NO_FEASIBLE_RESOURCE,
        PacketStatus.NO_FEASIBLE_RESOURCE,
    ]


def test_engine_expires_selected_packet_waiting_beyond_deadline() -> None:
    config = _config(deadline_slots=2)

    result = SimulationEngine(
        config,
        selectors={0: AfterDeadlineSelector(), 1: AfterDeadlineSelector()},
    ).run()

    assert not result.transmissions
    terminal = [
        record.status
        for record in result.lifecycle_records
        if record.status is PacketStatus.EXPIRED_WHILE_WAITING
    ]
    assert len(terminal) == 2

