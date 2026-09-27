from robosidelink.models import Resource
from robosidelink.observers.history import HistoryObserver


def test_snapshot_prunes_activity_outside_sensing_window() -> None:
    observer = HistoryObserver(sensing_window_slots=4)
    observer.record_activity(Resource(0, 0, 1), observed_slot=0, source_id=1)
    observer.record_activity(Resource(5, 1, 1), observed_slot=5, source_id=1)
    candidates = (
        Resource(9, 0, 1),
        Resource(9, 1, 1),
    )

    snapshot = observer.snapshot(decision_slot=8, candidate_resources=candidates)

    assert observer.observation_count == 1
    assert snapshot.evidence_by_resource[candidates[0]] == 0
    assert snapshot.evidence_by_resource[candidates[1]] == 1


def test_reservation_is_projected_at_its_interval() -> None:
    observer = HistoryObserver(sensing_window_slots=10)
    observer.record_activity(
        Resource(2, 1, 1),
        observed_slot=2,
        source_id=1,
        reservation_interval_slots=4,
    )
    projected = Resource(6, 1, 1)
    unrelated_slot = Resource(7, 1, 1)

    snapshot = observer.snapshot(
        decision_slot=5,
        candidate_resources=(projected, unrelated_slot),
    )

    assert snapshot.evidence_by_resource[projected] == 1
    assert snapshot.evidence_by_resource[unrelated_slot] == 0


def test_overlapping_reservation_evidence_accumulates() -> None:
    observer = HistoryObserver(sensing_window_slots=10)
    observer.record_activity(
        Resource(1, 0, 2),
        observed_slot=1,
        source_id=1,
        reservation_interval_slots=4,
    )
    observer.record_activity(
        Resource(1, 1, 1),
        observed_slot=1,
        source_id=2,
        reservation_interval_slots=4,
    )
    overlapping = Resource(5, 1, 1)
    unrelated = Resource(5, 3, 1)

    snapshot = observer.snapshot(
        decision_slot=2,
        candidate_resources=(overlapping, unrelated),
    )

    assert snapshot.evidence_by_resource[overlapping] == 2
    assert snapshot.evidence_by_resource[unrelated] == 0

