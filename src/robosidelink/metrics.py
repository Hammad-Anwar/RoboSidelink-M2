"""Metric collection and aggregation with explicit denominators."""

from __future__ import annotations

import math
import statistics
from collections import defaultdict
from typing import Iterable

from robosidelink.models import (
    LifecycleRecord,
    PacketStatus,
    SelectorDiagnostic,
    SimulationResult,
    Transmission,
    TransmissionStatus,
)


class MetricsCollector:
    def __init__(self) -> None:
        self.lifecycle_records: list[LifecycleRecord] = []
        self.transmissions: list[Transmission] = []
        self.selector_diagnostics: list[SelectorDiagnostic] = []

    def record_lifecycle(self, record: LifecycleRecord) -> None:
        self.lifecycle_records.append(record)

    def record_transmission(self, transmission: Transmission) -> None:
        self.transmissions.append(transmission)

    def record_selector(self, diagnostic: SelectorDiagnostic) -> None:
        self.selector_diagnostics.append(diagnostic)

    def summary(self, result: SimulationResult) -> dict[str, int | float | None]:
        generated = len(result.generated_packets)
        delivered_ids = {
            record.packet_id
            for record in result.lifecycle_records
            if record.status is PacketStatus.DELIVERED_ON_TIME
        }
        collided_attempts = sum(
            transmission.status is TransmissionStatus.COLLIDED
            for transmission in result.transmissions
        )
        attempts = len(result.transmissions)

        occupied_cells = {
            (transmission.resource.slot, subchannel)
            for transmission in result.transmissions
            for subchannel in range(
                transmission.resource.start_subchannel,
                transmission.resource.end_subchannel,
            )
        }
        total_cells = result.final_executed_slot * result.num_subchannels

        summary: dict[str, int | float | None] = {
            "generated_packets": generated,
            "delivered_packets": len(delivered_ids),
            "transmission_attempts": attempts,
            "collision_attempts": collided_attempts,
            "pdr": self._ratio(len(delivered_ids), generated),
            "on_time_delivery_ratio": self._ratio(len(delivered_ids), generated),
            "deadline_miss_ratio": self._ratio(
                generated - len(delivered_ids), generated
            ),
            "collision_attempt_ratio": self._ratio(collided_attempts, attempts),
            "resource_utilization": self._ratio(len(occupied_cells), total_cells),
        }

        events: dict[int, dict[PacketStatus, int]] = defaultdict(dict)
        for record in result.lifecycle_records:
            events[record.packet_id][record.status] = record.slot

        queueing: list[int] = []
        decision: list[int] = []
        access: list[int] = []
        end_to_end: list[int] = []
        for packet in result.generated_packets:
            if packet.packet_id not in delivered_ids:
                continue
            packet_events = events[packet.packet_id]
            queueing.append(
                packet_events[PacketStatus.SELECTION_REQUESTED]
                - packet_events[PacketStatus.GENERATED]
            )
            decision.append(
                packet_events[PacketStatus.SELECTED]
                - packet_events[PacketStatus.SELECTION_REQUESTED]
            )
            access.append(
                packet_events[PacketStatus.TRANSMISSION_STARTED]
                - packet_events[PacketStatus.SELECTED]
            )
            end_to_end.append(
                packet_events[PacketStatus.DELIVERED_ON_TIME]
                - packet_events[PacketStatus.GENERATED]
            )

        summary.update(self._latency_stats("queueing_latency_slots", queueing))
        summary.update(self._latency_stats("decision_latency_slots", decision))
        summary.update(self._latency_stats("resource_access_latency_slots", access))
        summary.update(self._latency_stats("end_to_end_latency_slots", end_to_end))
        return summary

    @staticmethod
    def _ratio(numerator: int, denominator: int) -> float | None:
        return numerator / denominator if denominator else None

    @classmethod
    def _latency_stats(
        cls, prefix: str, values: Iterable[int]
    ) -> dict[str, float | None]:
        sample = sorted(values)
        if not sample:
            return {
                f"{prefix}_mean": None,
                f"{prefix}_median": None,
                f"{prefix}_p95": None,
                f"{prefix}_p99": None,
                f"{prefix}_max": None,
            }
        return {
            f"{prefix}_mean": statistics.fmean(sample),
            f"{prefix}_median": float(statistics.median(sample)),
            f"{prefix}_p95": float(cls._nearest_rank(sample, 0.95)),
            f"{prefix}_p99": float(cls._nearest_rank(sample, 0.99)),
            f"{prefix}_max": float(sample[-1]),
        }

    @staticmethod
    def _nearest_rank(sorted_values: list[int], quantile: float) -> int:
        index = max(0, math.ceil(quantile * len(sorted_values)) - 1)
        return sorted_values[index]
