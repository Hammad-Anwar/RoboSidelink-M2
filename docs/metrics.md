# Metrics

All packet ratios use generated packets unless stated otherwise. Every generated packet reaches one terminal outcome because traffic generation stops at the configured horizon and the engine drains outstanding work.

## Reliability and deadline metrics

### Packet delivery ratio

```text
PDR = packets delivered successfully / packets generated
```

Version 0.1 uses a strict deadline policy: it never deliberately schedules a transmission that would complete after the deadline. Successful delivery is therefore on time, and PDR can equal the on-time delivery ratio.

### On-time delivery ratio

```text
on-time delivery ratio = packets delivered by deadline / packets generated
```

A transmission occupying slot `s` completes at boundary `s + 1`. Completion exactly at the packet's absolute deadline boundary is on time.

### Deadline-miss ratio

```text
deadline-miss ratio = packets not delivered by deadline / packets generated
```

Misses include collision, queued expiry, selected-but-waiting expiry, and absence of a feasible resource.

### Collision-attempt ratio

```text
collision-attempt ratio = collided transmission attempts / all transmission attempts
```

The denominator is attempts, not generated packets. Packets that expire without transmitting do not enter this denominator.

## Latency metrics

For delivered packets:

```text
queueing latency = selection-request slot - generation slot

modeled decision latency = decision-completion slot - selection-request slot

resource-access latency = transmission-start slot - decision-completion slot

end-to-end latency = reception-completion boundary - generation boundary
```

Each latency family reports:

- arithmetic mean;
- median;
- nearest-rank p95;
- nearest-rank p99;
- maximum.

If a run delivers no packets, its latency fields are null. They are never replaced with zero.

Multiply slot-valued latency by `slot_duration_ms` from the resolved configuration to obtain milliseconds.

## Resource utilization

```text
resource utilization = unique occupied resource cells / available resource cells
```

A resource cell is one `(slot, subchannel)` pair. Overlapping transmissions consume the same unique cell once in the utilization numerator even though they create multiple transmission attempts.

The denominator covers slot zero through the final executed slot, including the drain after traffic generation stops. Result metadata records both the generation horizon and final boundary.

## Experiment aggregation

Each seed is an independent observation. Selectors use the same declared seed list for paired comparison.

For every selector and robot count, `aggregate.csv` contains:

- arithmetic mean;
- lower 95% percentile-bootstrap bound;
- upper 95% percentile-bootstrap bound;
- number of independent seeds.

Bootstrap resampling is deterministic. The method, number of resamples, and bootstrap seed are stored in `experiment_metadata.json`. A group with only one seed retains its mean and reports null interval bounds.

## Populations and responsible comparison

- Delivery ratios describe all generated packets.
- Collision ratios describe only transmission attempts.
- Latencies describe successfully delivered packets.
- Utilization describes executed time-frequency cells.

These populations must remain visible when comparing algorithms. A selector that drops many packets before transmission can show a low collision-attempt ratio without providing good packet reliability.

