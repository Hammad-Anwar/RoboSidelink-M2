"""Bounded sensing history and reservation projection."""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType

from robosidelink.models import Resource
from robosidelink.observers.base import ObservationSnapshot


@dataclass(frozen=True)
class _ObservedActivity:
    resource: Resource
    observed_slot: int
    source_id: int
    reservation_interval_slots: int | None


class HistoryObserver:
    def __init__(self, sensing_window_slots: int) -> None:
        if sensing_window_slots <= 0:
            raise ValueError("sensing_window_slots must be positive")
        self.sensing_window_slots = sensing_window_slots
        self._history: list[_ObservedActivity] = []

    @property
    def observation_count(self) -> int:
        return len(self._history)

    def record_activity(
        self,
        resource: Resource,
        *,
        observed_slot: int,
        source_id: int,
        reservation_interval_slots: int | None = None,
    ) -> None:
        if observed_slot < 0:
            raise ValueError("observed_slot must be non-negative")
        if source_id < 0:
            raise ValueError("source_id must be non-negative")
        if reservation_interval_slots is not None and reservation_interval_slots <= 0:
            raise ValueError("reservation_interval_slots must be positive")
        self._history.append(
            _ObservedActivity(
                resource=resource,
                observed_slot=observed_slot,
                source_id=source_id,
                reservation_interval_slots=reservation_interval_slots,
            )
        )

    def snapshot(
        self,
        *,
        decision_slot: int,
        candidate_resources: tuple[Resource, ...],
    ) -> ObservationSnapshot:
        lower_bound = max(0, decision_slot - self.sensing_window_slots)
        self._history = [
            item
            for item in self._history
            if lower_bound <= item.observed_slot < decision_slot
        ]

        evidence: dict[Resource, int] = {}
        for candidate in candidate_resources:
            score = 0
            for activity in self._history:
                if not self._subchannels_overlap(candidate, activity.resource):
                    continue
                interval = activity.reservation_interval_slots
                if interval is None:
                    score += 1
                    continue
                delta = candidate.slot - activity.resource.slot
                if delta > 0 and delta % interval == 0:
                    score += 1
            evidence[candidate] = score
        return ObservationSnapshot(MappingProxyType(evidence))

    @staticmethod
    def _subchannels_overlap(left: Resource, right: Resource) -> bool:
        return (
            left.start_subchannel < right.end_subchannel
            and right.start_subchannel < left.end_subchannel
        )
