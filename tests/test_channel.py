from robosidelink.channel import DeterministicCollisionChannel
from robosidelink.models import (
    Packet,
    Resource,
    Transmission,
    TransmissionStatus,
)


def _transmission(packet_id: int, source: int, subchannel: int) -> Transmission:
    return Transmission(
        packet=Packet(
            packet_id=packet_id,
            source_id=source,
            destination_id=source + 10,
            generation_slot=0,
            deadline_slot=4,
            payload_size_bytes=64,
            priority=1,
        ),
        resource=Resource(slot=0, start_subchannel=subchannel, width=1),
    )


def test_overlapping_transmissions_collide() -> None:
    resolved = DeterministicCollisionChannel().resolve(
        (_transmission(0, 0, 1), _transmission(1, 1, 1))
    )

    assert [item.status for item in resolved] == [
        TransmissionStatus.COLLIDED,
        TransmissionStatus.COLLIDED,
    ]


def test_independent_resources_are_delivered() -> None:
    resolved = DeterministicCollisionChannel().resolve(
        (_transmission(0, 0, 0), _transmission(1, 1, 1))
    )

    assert all(item.status is TransmissionStatus.DELIVERED for item in resolved)


def test_only_overlapping_members_of_three_transmissions_collide() -> None:
    resolved = DeterministicCollisionChannel().resolve(
        (
            _transmission(0, 0, 0),
            _transmission(1, 1, 0),
            _transmission(2, 2, 2),
        )
    )

    assert [item.status for item in resolved] == [
        TransmissionStatus.COLLIDED,
        TransmissionStatus.COLLIDED,
        TransmissionStatus.DELIVERED,
    ]

