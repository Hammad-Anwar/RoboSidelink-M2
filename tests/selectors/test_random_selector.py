import random

from robosidelink.models import Packet, PacketStatus, Resource
from robosidelink.selectors.base import SelectionContext
from robosidelink.selectors.random_selector import RandomSelector


def _packet() -> Packet:
    return Packet(
        packet_id=1,
        source_id=0,
        destination_id=1,
        generation_slot=0,
        deadline_slot=8,
        payload_size_bytes=64,
        priority=1,
    )


def _context(candidates: tuple[Resource, ...]) -> SelectionContext:
    return SelectionContext(
        node_id=0,
        packet=_packet(),
        request_slot=0,
        decision_slot=0,
        candidates=candidates,
        observation=None,
    )


def test_random_selector_returns_one_of_the_supplied_candidates() -> None:
    candidates = (
        Resource(slot=1, start_subchannel=0, width=1),
        Resource(slot=1, start_subchannel=1, width=1),
    )

    decision = RandomSelector(random.Random(42)).select(_context(candidates))

    assert decision.resource in candidates
    assert decision.terminal_status is None
    assert decision.policy == "random"
    assert decision.initial_candidate_count == 2
    assert decision.retained_candidate_count == 2


def test_random_selector_is_reproducible_for_same_seed() -> None:
    candidates = tuple(
        Resource(slot=1, start_subchannel=index, width=1) for index in range(4)
    )

    first = RandomSelector(random.Random(42)).select(_context(candidates))
    second = RandomSelector(random.Random(42)).select(_context(candidates))

    assert first == second


def test_random_selector_returns_terminal_decision_for_no_candidates() -> None:
    decision = RandomSelector(random.Random(42)).select(_context(()))

    assert decision.resource is None
    assert decision.terminal_status is PacketStatus.NO_FEASIBLE_RESOURCE
    assert decision.initial_candidate_count == 0
    assert decision.retained_candidate_count == 0
