import random
from dataclasses import replace
from pathlib import Path
from types import MappingProxyType

from robosidelink.config import load_config
from robosidelink.models import (
    Packet,
    ReservationState,
    Resource,
    ResourceOffset,
)
from robosidelink.observers.base import ObservationSnapshot
from robosidelink.selectors.base import SelectionContext
from robosidelink.selectors.mode2 import Rel16Mode2InspiredSelector


def _packet() -> Packet:
    return Packet(0, 0, 1, 0, 12, 64, 1)


def _selector(*, minimum_fraction: float = 0.2) -> Rel16Mode2InspiredSelector:
    config = load_config(Path("configs/quickstart.yaml"))
    mode2 = replace(
        config.selector.mode2,
        minimum_candidate_fraction=minimum_fraction,
        initial_evidence_threshold=0,
        reselection_counter_min=2,
        reselection_counter_max=2,
    )
    return Rel16Mode2InspiredSelector(
        mode2,
        choice_rng=random.Random(7),
        counter_rng=random.Random(8),
        keep_rng=random.Random(9),
    )


def _context(
    candidates: tuple[Resource, ...], evidence: dict[Resource, int]
) -> SelectionContext:
    return SelectionContext(
        node_id=0,
        packet=_packet(),
        request_slot=0,
        decision_slot=0,
        candidates=candidates,
        observation=ObservationSnapshot(MappingProxyType(evidence)),
    )


def test_mode2_excludes_candidates_above_evidence_threshold() -> None:
    candidates = tuple(Resource(1, index, 1) for index in range(3))
    evidence = {candidates[0]: 0, candidates[1]: 1, candidates[2]: 2}

    decision = _selector().select(_context(candidates, evidence))

    assert decision.resource == candidates[0]
    assert decision.policy == "rel16-mode2-inspired"
    assert decision.initial_candidate_count == 3
    assert decision.excluded_candidate_count == 2
    assert decision.retained_candidate_count == 1
    assert decision.relaxation_level == 0


def test_mode2_relaxes_integer_evidence_until_minimum_fraction_remains() -> None:
    candidates = tuple(Resource(1, index, 1) for index in range(4))
    evidence = {
        candidates[0]: 1,
        candidates[1]: 1,
        candidates[2]: 2,
        candidates[3]: 2,
    }

    decision = _selector(minimum_fraction=0.5).select(
        _context(candidates, evidence)
    )

    assert decision.resource in candidates[:2]
    assert decision.retained_candidate_count == 2
    assert decision.excluded_candidate_count == 2
    assert decision.relaxation_level == 1


def test_mode2_empty_candidates_returns_no_feasible_decision() -> None:
    decision = _selector().select(_context((), {}))

    assert decision.resource is None
    assert decision.terminal_status.value == "no_feasible_resource"


def test_mode2_uses_later_reserved_candidate_inside_selection_window() -> None:
    reserved = Resource(9, 2, 1)
    alternative = Resource(9, 0, 1)
    context = replace(
        _context((alternative, reserved), {alternative: 0, reserved: 10}),
        decision_slot=2,
        reservation_state=ReservationState(
            resource_offset=ResourceOffset(1, 2, 1),
            reservation_interval_slots=4,
            remaining_reselections=2,
            keep_probability=0.5,
        ),
    )

    decision = _selector().select(context)

    assert decision.resource == reserved
    assert decision.retained_candidate_count == 1
