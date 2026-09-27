import random

from robosidelink.models import ReservationState, ResourceOffset
from robosidelink.selectors.mode2 import advance_reservation


def _state(*, remaining: int, keep_probability: float) -> ReservationState:
    return ReservationState(
        resource_offset=ResourceOffset(slot_offset=1, start_subchannel=2, width=1),
        reservation_interval_slots=4,
        remaining_reselections=remaining,
        keep_probability=keep_probability,
    )


def test_reservation_projects_next_matching_resource() -> None:
    resource = _state(remaining=3, keep_probability=0.5).next_resource_at_or_after(6)

    assert resource.slot == 9
    assert resource.start_subchannel == 2


def test_reservation_counter_decrements_without_reselection() -> None:
    update = advance_reservation(
        _state(remaining=3, keep_probability=0.5),
        keep_rng=random.Random(1),
        counter_rng=random.Random(2),
        counter_min=5,
        counter_max=7,
    )

    assert not update.requires_reselection
    assert update.state is not None
    assert update.state.remaining_reselections == 2


def test_keep_probability_one_renews_counter_in_inclusive_bounds() -> None:
    update = advance_reservation(
        _state(remaining=1, keep_probability=1.0),
        keep_rng=random.Random(1),
        counter_rng=random.Random(2),
        counter_min=5,
        counter_max=7,
    )

    assert not update.requires_reselection
    assert update.state is not None
    assert 5 <= update.state.remaining_reselections <= 7


def test_keep_probability_zero_requires_reselection() -> None:
    update = advance_reservation(
        _state(remaining=1, keep_probability=0.0),
        keep_rng=random.Random(1),
        counter_rng=random.Random(2),
        counter_min=5,
        counter_max=7,
    )

    assert update.requires_reselection
    assert update.state is None

