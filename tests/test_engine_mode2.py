from dataclasses import replace
from pathlib import Path

from robosidelink.config import load_config
from robosidelink.engine import SimulationEngine
from robosidelink.models import PacketStatus, Resource, SelectionDecision
from robosidelink.selectors.base import SelectionContext


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


def test_engine_mode2_avoids_projected_reservation() -> None:
    config = load_config(Path("configs/quickstart.yaml"))
    config = replace(
        config,
        simulation=replace(config.simulation, duration_slots=1),
        selector=replace(
            config.selector,
            policy="rel16-mode2-inspired",
            processing_delay_slots=1,
            mode2=replace(
                config.selector.mode2,
                t1_slots=1,
                t2_slots=3,
                reservation_interval_slots=1,
                minimum_candidate_fraction=0.2,
                initial_evidence_threshold=0,
            ),
        ),
    )
    engine = SimulationEngine(config, selectors={1: NoResourceSelector()})
    engine.observer_for(0).record_activity(
        Resource(0, 0, 1),
        observed_slot=0,
        source_id=99,
        reservation_interval_slots=1,
    )

    result = engine.run()

    node_zero = next(item for item in result.selector_diagnostics if item.node_id == 0)
    assert node_zero.policy == "rel16-mode2-inspired"
    assert node_zero.selected_resource is not None
    assert node_zero.selected_resource.start_subchannel != 0
    assert node_zero.excluded_candidate_count > 0
