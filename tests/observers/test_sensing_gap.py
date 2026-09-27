from dataclasses import replace
from pathlib import Path

from robosidelink.config import load_config
from robosidelink.engine import SimulationEngine
from robosidelink.models import PacketStatus, SelectionDecision
from robosidelink.selectors.base import SelectionContext


class FirstCandidateSelector:
    policy_name = "first-test"

    def select(self, context: SelectionContext) -> SelectionDecision:
        resource = context.candidates[0]
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


class NoResourceSelector:
    policy_name = "none-test"

    def select(self, context: SelectionContext) -> SelectionDecision:
        return SelectionDecision(
            resource=None,
            terminal_status=PacketStatus.NO_FEASIBLE_RESOURCE,
            policy=self.policy_name,
            request_slot=context.request_slot,
            decision_slot=context.decision_slot,
            initial_candidate_count=len(context.candidates),
            excluded_candidate_count=0,
            retained_candidate_count=0,
        )


def test_transmitting_node_has_sensing_gap_while_idle_node_observes() -> None:
    config = load_config(Path("configs/quickstart.yaml"))
    config = replace(
        config,
        simulation=replace(config.simulation, duration_slots=1),
        scenario=replace(config.scenario, num_robots=4),
    )
    engine = SimulationEngine(
        config,
        selectors={
            0: FirstCandidateSelector(),
            1: FirstCandidateSelector(),
            2: NoResourceSelector(),
            3: NoResourceSelector(),
        },
    )

    engine.run()

    assert engine.observer_for(0).observation_count == 0
    assert engine.observer_for(2).observation_count == 2
