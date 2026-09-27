import pytest

from robosidelink.metrics import MetricsCollector
from robosidelink.models import (
    LifecycleRecord,
    Packet,
    PacketStatus,
    Resource,
    SimulationResult,
    Transmission,
    TransmissionStatus,
)


def _packet(packet_id: int, generation_slot: int = 0) -> Packet:
    return Packet(
        packet_id=packet_id,
        source_id=packet_id * 2,
        destination_id=packet_id * 2 + 1,
        generation_slot=generation_slot,
        deadline_slot=generation_slot + 4,
        payload_size_bytes=64,
        priority=1,
    )


def test_summary_uses_generated_packets_as_delivery_denominator() -> None:
    packets = tuple(_packet(index, generation_slot=int(index == 3)) for index in range(4))
    lifecycle = (
        LifecycleRecord(0, 0, PacketStatus.GENERATED, 0),
        LifecycleRecord(0, 0, PacketStatus.SELECTION_REQUESTED, 1),
        LifecycleRecord(0, 0, PacketStatus.SELECTED, 1),
        LifecycleRecord(0, 0, PacketStatus.TRANSMISSION_STARTED, 2),
        LifecycleRecord(0, 0, PacketStatus.DELIVERED_ON_TIME, 3),
        LifecycleRecord(1, 2, PacketStatus.GENERATED, 0),
        LifecycleRecord(1, 2, PacketStatus.SELECTION_REQUESTED, 0),
        LifecycleRecord(1, 2, PacketStatus.SELECTED, 0),
        LifecycleRecord(1, 2, PacketStatus.TRANSMISSION_STARTED, 0),
        LifecycleRecord(1, 2, PacketStatus.COLLIDED, 1),
        LifecycleRecord(2, 4, PacketStatus.GENERATED, 0),
        LifecycleRecord(2, 4, PacketStatus.EXPIRED_WHILE_QUEUED, 2),
        LifecycleRecord(3, 6, PacketStatus.GENERATED, 1),
        LifecycleRecord(3, 6, PacketStatus.NO_FEASIBLE_RESOURCE, 1),
    )
    transmissions = (
        Transmission(
            packets[0],
            Resource(2, 0, 1),
            TransmissionStatus.DELIVERED,
        ),
        Transmission(
            packets[1],
            Resource(0, 1, 1),
            TransmissionStatus.COLLIDED,
        ),
    )
    result = SimulationResult(
        generated_packets=packets,
        transmissions=transmissions,
        lifecycle_records=lifecycle,
        selector_diagnostics=(),
        generation_horizon_slot=2,
        final_executed_slot=4,
        num_subchannels=4,
    )

    summary = MetricsCollector().summary(result)

    assert summary["generated_packets"] == 4
    assert summary["delivered_packets"] == 1
    assert summary["pdr"] == pytest.approx(0.25)
    assert summary["on_time_delivery_ratio"] == pytest.approx(0.25)
    assert summary["deadline_miss_ratio"] == pytest.approx(0.75)
    assert summary["collision_attempt_ratio"] == pytest.approx(0.5)
    assert summary["resource_utilization"] == pytest.approx(0.125)
    assert summary["queueing_latency_slots_mean"] == pytest.approx(1.0)
    assert summary["decision_latency_slots_mean"] == pytest.approx(0.0)
    assert summary["resource_access_latency_slots_mean"] == pytest.approx(1.0)
    assert summary["end_to_end_latency_slots_mean"] == pytest.approx(3.0)
    assert summary["end_to_end_latency_slots_median"] == pytest.approx(3.0)
    assert summary["end_to_end_latency_slots_p95"] == pytest.approx(3.0)
    assert summary["end_to_end_latency_slots_p99"] == pytest.approx(3.0)
    assert summary["end_to_end_latency_slots_max"] == pytest.approx(3.0)


def test_latency_statistics_are_none_when_nothing_is_delivered() -> None:
    packet = _packet(0)
    result = SimulationResult(
        generated_packets=(packet,),
        transmissions=(
            Transmission(
                packet,
                Resource(0, 0, 1),
                TransmissionStatus.COLLIDED,
            ),
        ),
        lifecycle_records=(
            LifecycleRecord(0, 0, PacketStatus.GENERATED, 0),
            LifecycleRecord(0, 0, PacketStatus.COLLIDED, 1),
        ),
        selector_diagnostics=(),
        generation_horizon_slot=1,
        final_executed_slot=1,
        num_subchannels=1,
    )

    summary = MetricsCollector().summary(result)

    assert summary["end_to_end_latency_slots_mean"] is None
    assert summary["end_to_end_latency_slots_p95"] is None

