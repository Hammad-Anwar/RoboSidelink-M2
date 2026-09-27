"""Enumeration of valid time-frequency resources."""

from dataclasses import dataclass

from robosidelink.models import Resource


@dataclass(frozen=True)
class ResourcePool:
    num_subchannels: int

    def __post_init__(self) -> None:
        if self.num_subchannels <= 0:
            raise ValueError("num_subchannels must be positive")

    def candidates(
        self, start_slot: int, end_slot: int, width: int
    ) -> tuple[Resource, ...]:
        """Enumerate inclusive slot bounds in stable slot-major order."""
        if start_slot < 0:
            raise ValueError("start_slot must be non-negative")
        if end_slot < start_slot:
            raise ValueError("end_slot must be greater than or equal to start_slot")
        if width <= 0:
            raise ValueError("width must be positive")
        if width > self.num_subchannels:
            raise ValueError("width must not exceed num_subchannels")

        return tuple(
            Resource(slot=slot, start_subchannel=start, width=width)
            for slot in range(start_slot, end_slot + 1)
            for start in range(self.num_subchannels - width + 1)
        )

