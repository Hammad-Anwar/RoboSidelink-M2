from dataclasses import replace
from pathlib import Path

from robosidelink.config import load_config
from robosidelink.engine import SimulationEngine
from robosidelink.models import PacketStatus, SelectionDecision
from robosidelink.selectors.base import SelectionContext


class LastCandidateSelector:
    policy_name = "last-test"

    def select(self, context: SelectionContext) -> SelectionDecision:
        resource = context.candidates[-1]
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


def test_engine_drains_packets_generated_near_horizon() -> None:
    config = load_config(Path("configs/quickstart.yaml"))
    config = replace(
        config,
        simulation=replace(config.simulation, duration_slots=1),
        traffic=replace(config.traffic, deadline_slots=4),
        selector=replace(
            config.selector,
            mode2=replace(config.selector.mode2, t1_slots=0, t2_slots=3),
        ),
    )
    selectors = {0: LastCandidateSelector(), 1: LastCandidateSelector()}

    result = SimulationEngine(config, selectors=selectors).run()

    assert result.generation_horizon_slot == 1
    assert result.final_executed_slot == 4
    assert len(result.generated_packets) == 2
    terminal_packet_ids = {
        record.packet_id
        for record in result.lifecycle_records
        if record.status in {PacketStatus.DELIVERED_ON_TIME, PacketStatus.COLLIDED}
    }
    assert terminal_packet_ids == {0, 1}
