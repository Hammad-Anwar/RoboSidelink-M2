import pytest

from robosidelink.models import Resource
from robosidelink.resource_pool import ResourcePool


def test_candidates_are_inclusive_and_stably_ordered() -> None:
    pool = ResourcePool(num_subchannels=4)

    candidates = pool.candidates(start_slot=5, end_slot=6, width=2)

    assert candidates == (
        Resource(slot=5, start_subchannel=0, width=2),
        Resource(slot=5, start_subchannel=1, width=2),
        Resource(slot=5, start_subchannel=2, width=2),
        Resource(slot=6, start_subchannel=0, width=2),
        Resource(slot=6, start_subchannel=1, width=2),
        Resource(slot=6, start_subchannel=2, width=2),
    )


@pytest.mark.parametrize(
    ("start_slot", "end_slot", "width", "message"),
    [
        (4, 3, 1, "end_slot"),
        (0, 1, 0, "width"),
        (0, 1, 5, "num_subchannels"),
    ],
)
def test_candidates_reject_invalid_ranges(
    start_slot: int, end_slot: int, width: int, message: str
) -> None:
    pool = ResourcePool(num_subchannels=4)

    with pytest.raises(ValueError, match=message):
        pool.candidates(start_slot=start_slot, end_slot=end_slot, width=width)


def test_pool_rejects_non_positive_subchannel_count() -> None:
    with pytest.raises(ValueError, match="num_subchannels"):
        ResourcePool(num_subchannels=0)

