"""Deterministic collision-only reception model."""

from dataclasses import replace

from robosidelink.models import Transmission, TransmissionStatus


class DeterministicCollisionChannel:
    def resolve(
        self, transmissions: tuple[Transmission, ...]
    ) -> tuple[Transmission, ...]:
        resolved: list[Transmission] = []
        for index, transmission in enumerate(transmissions):
            collided = any(
                transmission.resource.overlaps(other.resource)
                for other_index, other in enumerate(transmissions)
                if other_index != index
            )
            status = (
                TransmissionStatus.COLLIDED
                if collided
                else TransmissionStatus.DELIVERED
            )
            resolved.append(replace(transmission, status=status))
        return tuple(resolved)

