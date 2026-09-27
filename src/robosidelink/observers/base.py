"""Immutable observation information exposed to selectors."""

from dataclasses import dataclass
from typing import Mapping

from robosidelink.models import Resource


@dataclass(frozen=True)
class ObservationSnapshot:
    evidence_by_resource: Mapping[Resource, int]

