from dataclasses import replace
from pathlib import Path

from robosidelink.config import load_config
from robosidelink.engine import SimulationEngine
from robosidelink.models import SelectionDecision, TransmissionStatus
from robosidelink.selectors.base import SelectionContext


class FixedSubchannelSelector:
    policy_name = "fixed-test"

    def __init__(self, subchannel: int) -> None:
        self.subchannel = subchannel

    def select(self, context: SelectionContext) -> SelectionDecision:
        resource = next(
            candidate
            for candidate in context.candidates
            if candidate.start_subchannel == self.subchannel
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


def _single_generation_config():
    config = load_config(Path("configs/quickstart.yaml"))
    return replace(
        config,
        simulation=replace(config.simulation, duration_slots=1),
    )


def test_engine_delivers_two_nodes_on_different_resources() -> None:
    engine = SimulationEngine(
        _single_generation_config(),
        selectors={0: FixedSubchannelSelector(0), 1: FixedSubchannelSelector(1)},
    )

    result = engine.run()

    assert len(result.generated_packets) == 2
    assert len(result.transmissions) == 2
    assert all(
        transmission.status is TransmissionStatus.DELIVERED
        for transmission in result.transmissions
    )


def test_engine_resolves_same_slot_transmissions_as_one_collision_batch() -> None:
    engine = SimulationEngine(
        _single_generation_config(),
        selectors={0: FixedSubchannelSelector(0), 1: FixedSubchannelSelector(0)},
    )

    result = engine.run()

    assert len(result.transmissions) == 2
    assert {transmission.resource.slot for transmission in result.transmissions} == {0}
    assert all(
        transmission.status is TransmissionStatus.COLLIDED
        for transmission in result.transmissions
    )
    assert result.final_executed_slot == 1
