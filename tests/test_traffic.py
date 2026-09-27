import random

import pytest

from robosidelink.traffic import (
    JitteredPeriodicTrafficGenerator,
    PeriodicTrafficGenerator,
)


def test_periodic_generator_emits_on_period_boundaries() -> None:
    generator = PeriodicTrafficGenerator(period_slots=2)

    assert [slot for slot in range(6) if generator.arrivals_at(slot)] == [0, 2, 4]


def test_zero_jitter_matches_periodic_next_arrival() -> None:
    generator = JitteredPeriodicTrafficGenerator(
        period_slots=4,
        jitter_slots=0,
        rng=random.Random(7),
    )

    assert generator.next_arrival(after_slot=3) == 7


def test_jittered_arrival_stays_within_configured_bound() -> None:
    generator = JitteredPeriodicTrafficGenerator(
        period_slots=4,
        jitter_slots=1,
        rng=random.Random(7),
    )

    assert 6 <= generator.next_arrival(after_slot=3) <= 8


def test_traffic_generators_reject_invalid_period() -> None:
    with pytest.raises(ValueError, match="period_slots"):
        PeriodicTrafficGenerator(period_slots=0)

