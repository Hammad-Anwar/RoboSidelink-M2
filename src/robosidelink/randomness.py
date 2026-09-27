"""Stable, independently consumable random streams."""

from __future__ import annotations

import hashlib
import random


class NamedRandomStreams:
    """Derive and cache deterministic random generators by semantic name."""

    def __init__(self, root_seed: int) -> None:
        if root_seed < 0:
            raise ValueError("root_seed must be non-negative")
        self.root_seed = root_seed
        self._streams: dict[str, random.Random] = {}

    def rng(self, name: str) -> random.Random:
        if not name:
            raise ValueError("stream name must not be empty")
        if name not in self._streams:
            payload = f"{self.root_seed}:{name}".encode("utf-8")
            digest = hashlib.sha256(payload).digest()
            derived_seed = int.from_bytes(digest[:8], byteorder="big", signed=False)
            self._streams[name] = random.Random(derived_seed)
        return self._streams[name]
