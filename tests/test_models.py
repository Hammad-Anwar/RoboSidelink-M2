from dataclasses import FrozenInstanceError

import pytest

from robosidelink.models import Packet, Resource


def test_resource_overlap_detects_intersecting_subchannels_in_same_slot() -> None:
    left = Resource(slot=7, start_subchannel=1, width=2)
    right = Resource(slot=7, start_subchannel=2, width=2)

    assert left.overlaps(right)
    assert right.overlaps(left)


def test_resource_overlap_excludes_touching_subchannel_intervals() -> None:
    left = Resource(slot=7, start_subchannel=0, width=2)
    right = Resource(slot=7, start_subchannel=2, width=2)

    assert not left.overlaps(right)


def test_resource_overlap_requires_same_slot() -> None:
    left = Resource(slot=7, start_subchannel=1, width=2)
    right = Resource(slot=8, start_subchannel=1, width=2)

    assert not left.overlaps(right)


@pytest.mark.parametrize(
    ("kwargs", "field"),
    [
        ({"slot": -1, "start_subchannel": 0, "width": 1}, "slot"),
        ({"slot": 0, "start_subchannel": -1, "width": 1}, "start_subchannel"),
        ({"slot": 0, "start_subchannel": 0, "width": 0}, "width"),
    ],
)
def test_resource_rejects_invalid_coordinates(kwargs: dict, field: str) -> None:
    with pytest.raises(ValueError, match=field):
        Resource(**kwargs)


def test_packet_is_immutable_and_uses_absolute_deadline_boundary() -> None:
    packet = Packet(
        packet_id=3,
        source_id=0,
        destination_id=1,
        generation_slot=8,
        deadline_slot=20,
        payload_size_bytes=64,
        priority=1,
    )

    assert packet.deadline_slot == 20
    with pytest.raises(FrozenInstanceError):
        packet.deadline_slot = 21  # type: ignore[misc]


def test_packet_rejects_deadline_at_generation_boundary() -> None:
    with pytest.raises(ValueError, match="deadline_slot"):
        Packet(
            packet_id=3,
            source_id=0,
            destination_id=1,
            generation_slot=8,
            deadline_slot=8,
            payload_size_bytes=64,
            priority=1,
        )

