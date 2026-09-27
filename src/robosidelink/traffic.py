"""Packet-arrival processes expressed in integer slots."""

from __future__ import annotations

import random
from dataclasses import dataclass


@dataclass(frozen=True)
class PeriodicTrafficGenerator:
    period_slots: int
    start_slot: int = 0

    def __post_init__(self) -> None:
        if self.period_slots <= 0:
            raise ValueError("period_slots must be positive")
        if self.start_slot < 0:
            raise ValueError("start_slot must be non-negative")

    def arrivals_at(self, slot: int) -> int:
        if slot < self.start_slot:
            return 0
        return int((slot - self.start_slot) % self.period_slots == 0)


class JitteredPeriodicTrafficGenerator:
    def __init__(
        self,
        period_slots: int,
        jitter_slots: int,
        rng: random.Random,
    ) -> None:
        if period_slots <= 0:
            raise ValueError("period_slots must be positive")
        if jitter_slots < 0 or jitter_slots >= period_slots:
            raise ValueError("jitter_slots must satisfy 0 <= jitter_slots < period_slots")
        self.period_slots = period_slots
        self.jitter_slots = jitter_slots
        self._rng = rng

    def next_arrival(self, after_slot: int) -> int:
        offset = self._rng.randint(-self.jitter_slots, self.jitter_slots)
        return after_slot + self.period_slots + offset

