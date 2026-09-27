# RoboSidelink-M2

A reproducible, slot-level Python simulator for studying autonomous sidelink resource selection in cooperative-robot communication.

RoboSidelink-M2 compares uniform random resource selection with a documented **3GPP Release 16 Mode 2-inspired** sensing and reservation procedure. It measures how contention, resource access, collisions, and packet deadlines interact as the number of robots increases.

> **Research scope:** This is a transparent MAC/resource-selection abstraction. It is not a standards-compliant NR implementation and does not model SINR, propagation, decoding, HARQ, or the complete 3GPP protocol stack.

## Current status

Version 0.1 is runnable and tested.

| Capability | Status |
|---|---|
| Integer-slot simulation engine | Implemented |
| Periodic and jittered-periodic traffic | Implemented |
| Paired robot unicast | Implemented |
| Packet queues and strict deadlines | Implemented |
| Deterministic overlapping-resource collisions | Implemented |
| Uniform random selector | Implemented |
| Historical sensing and reservation projection | Implemented |
| Rel.16 Mode 2-inspired selector | Implemented |
| Semi-persistent reservation and reselection state | Implemented |
| Packet-level CSV and aggregate metrics | Implemented |
| Multi-seed density sweep and plots | Implemented |
| Groupcast, SINR, HARQ, ns-3/5G-LENA, SNN | Planned |

## Why this project exists

Cooperative robots exchange time-sensitive state and control messages. When infrastructure scheduling is unavailable, NR sidelink Mode 2 lets devices choose resources autonomously from a configured pool. The research question is whether that autonomous procedure can provide dependable delivery inside tight packet-delay budgets as traffic and robot density increase.

The simulator isolates that MAC-layer problem. It deliberately avoids detailed PHY behavior so every selection, exclusion, collision, and deadline miss can be inspected. A later ns-3/5G-LENA study can reuse the same scenarios and metrics for higher-fidelity validation.

## Five-minute quick start

Requirements:

- Python 3.11 or newer
- Git only if you want version metadata in results

### Windows PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
python -m robosidelink simulate --config configs/quickstart.yaml
```

### Linux or macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
python -m robosidelink simulate --config configs/quickstart.yaml
```

The command prints a concise metric summary and the absolute result directory. To select the directory explicitly:

```bash
python -m robosidelink simulate \
  --config configs/quickstart.yaml \
  --output results/quickstart
```

Existing non-empty result directories are rejected. Add `--overwrite` only when replacing that exact result directory is intentional.

## Run the density comparison

The checked-in demonstration profile compares both selectors at 2, 4, 8, 16, and 32 robots using the same five seeds:

```bash
python experiments/run_density_sweep.py \
  --config configs/density_sweep.yaml \
  --output results/density_demo

python scripts/plot_density_sweep.py \
  --input results/density_demo \
  --output results/density_demo/plots
```

PowerShell accepts the same commands on one line or with its backtick continuation character.

The demonstration produces:

- on-time delivery ratio versus robot count;
- collision-attempt ratio versus robot count;
- p95 end-to-end latency versus robot count;
- resource utilization versus robot count.

In the included short demonstration profile, the random selector's mean on-time delivery ratio falls from about `0.98` at two robots to about `0.38` at 32 robots. The Mode 2-inspired selector follows the same congestion trend. These values demonstrate simulator behavior only; five seeds, a deterministic collision channel, and a short generation horizon are not evidence of real factory-radio performance.

## How the simulator works

```text
YAML configuration
       |
       v
Traffic generators --> per-node FIFO queues
                              |
                              v
Historical observer --> resource selector --> future resource
                                               |
                                               v
                          same-slot batch collision resolution
                                               |
                                               v
                    lifecycle records, metrics, CSV, and plots
```

All internal time uses integer slot boundaries. A packet generated at boundary `g` with a deadline of `d` slots must complete by boundary `g + d`. A transmission occupying slot `s` completes at boundary `s + 1`.

The simulation distinguishes:

- **queueing latency:** generation to selection request;
- **modeled decision latency:** selection request to decision completion;
- **resource-access latency:** decision completion to transmission start;
- **end-to-end latency:** generation to reception completion.

The historical sensing-window length is not treated as time spent waiting before every decision. It defines how much past channel information is available at the decision slot. This distinction is important when evaluating tight packet-delay budgets.

## Resource model

A candidate resource is:

```text
(slot index, starting subchannel, contiguous subchannel width)
```

Two transmissions collide when they occupy the same slot and their subchannel intervals overlap. All robots currently share one mutual-interference domain. A collision causes every overlapping transmission to fail; otherwise reception succeeds at the end of the slot.

This deterministic model measures resource conflicts. It does not estimate radio-link reliability.

## Selection policies

### `random`

Selects uniformly from all future candidates that can complete before the packet deadline. It ignores sensing information.

### `rel16-mode2-inspired`

The baseline:

1. creates deadline-feasible candidates in `[n + T1, n + T2]`;
2. reads a bounded history of observable channel activity;
3. projects announced periodic reservations into the selection window;
4. scores candidates using deterministic occupancy evidence;
5. excludes candidates above the current evidence threshold;
6. relaxes that integer threshold if too few candidates remain;
7. selects uniformly from the retained candidates;
8. maintains a configurable semi-persistent reservation, reselection counter, and keep probability.

The evidence score replaces RSRP and the integer relaxation is not equivalent to the standard's 3 dB RSRP-threshold steps. See [Rel.16 traceability](docs/rel16-traceability.md) for the exact mapping.

## Configuration

Example:

```yaml
simulation:
  duration_ms: 20.0
  slot_duration_ms: 0.25
  seed: 42

radio:
  num_subchannels: 4
  resource_width_subchannels: 1

traffic:
  kind: periodic
  period_ms: 2.0
  jitter_ms: 0.0
  packet_size_bytes: 64
  deadline_ms: 3.0

scenario:
  num_robots: 2

selector:
  policy: random
  processing_delay_ms: 0.0
  mode2:
    sensing_window_ms: 100.0
    t1_ms: 0.0
    t2_ms: 2.0
    reservation_interval_ms: 2.0
    reselection_counter_min: 5
    reselection_counter_max: 15
    keep_probability: 0.5
    minimum_candidate_fraction: 0.2
    initial_evidence_threshold: 0
```

Durations must convert to a whole number of slots; the loader never silently rounds scientific inputs. Unknown keys, odd robot counts, invalid probabilities, impossible subchannel widths, and inconsistent windows fail before simulation begins.

The simulation duration is the packet-generation horizon. After generation stops, the engine drains all outstanding packets to terminal outcomes so late-horizon packets remain in metric denominators.

## Result files

Each run writes atomically:

```text
config.original.yaml
config.resolved.yaml
metadata.json
packets.csv
transmissions.csv
selector_diagnostics.csv
metrics.json
```

Metadata includes the seed, simulator version, Git commit when available, a dirty-working-tree indicator, UTC execution time, generation horizon, and final executed slot. Scientific CSV and JSON outputs are deterministic for the same version, resolved configuration, and seed; timestamps and repository state are isolated in metadata.

The density experiment additionally writes:

```text
per_run.csv
aggregate.csv
experiment_metadata.json
runs/<selector>/nodes-<N>/seed-<seed>/...
```

Confidence intervals are deterministic 95% percentile-bootstrap intervals across independent seeds. The method, resample count, and bootstrap seed are recorded in `experiment_metadata.json`.

## Metrics

Primary metrics are:

- packet delivery ratio;
- on-time delivery ratio;
- deadline-miss ratio;
- collision-attempt ratio;
- queueing, decision, resource-access, and end-to-end latency;
- resource utilization.

Latency summaries use delivered packets and report mean, median, p95, p99, and maximum. Runs with no delivered packets report null latency statistics rather than zero. Exact formulas and populations are documented in [metrics.md](docs/metrics.md).

## Reproducibility

One root seed deterministically creates independent named streams for:

- each node's traffic jitter;
- candidate choice;
- reservation counters;
- reservation keep decisions.

Consuming more random values in one subsystem does not change the sequence used by another subsystem. Density comparisons reuse the same declared seeds for both selectors.

## Testing

Run the full suite:

```bash
python -m pytest -q
```

Run with coverage:

```bash
python -m pytest --cov=robosidelink --cov-report=term-missing -q
```

The suite covers slot conversion, configuration errors, independent random streams, resource overlap, deadline boundaries, collision batches, sensing history, own-transmission sensing gaps, reservation projection, exclusion relaxation, semi-persistent state, lifecycle metrics, atomic output, CLI behavior, density aggregation, bootstrap intervals, and plot generation.

## Repository layout

```text
configs/                 Reproducible run and experiment profiles
src/robosidelink/        Simulator package
  observers/             Per-node historical sensing
  selectors/             Random and Mode 2-inspired policies
experiments/             Multi-run experiment orchestration
scripts/                 Plotting from saved results
tests/                   Unit and integration tests
docs/                    Scope, metrics, standards mapping, and project plan
results/                 Generated output; ignored by Git except .gitkeep
```

## Limitations

- Occupancy evidence is deterministic and does not model RSRP.
- Observable reservations are perfect; SCI decoding errors are absent.
- Every node is in one interference domain; hidden terminals and capture are absent.
- A packet has one transmission attempt; HARQ is absent.
- Successful reception is guaranteed when no resource overlap exists.
- Only paired unicast is implemented.
- The processing delay is a configurable sensitivity parameter, not a measured modem implementation value.
- The current experiment is not validated against ns-3/5G-LENA or hardware.

See [model-scope.md](docs/model-scope.md) before interpreting results.

## Roadmap

1. sensing-window and packet-deadline sweeps;
2. most-recent-slot and instantaneous-observation selectors;
3. deadline-aware selection;
4. groupcast semantics and experiments;
5. SINR and factory-channel extensions;
6. selected scenario reproduction in ns-3/5G-LENA;
7. optional event-driven or SNN inference with separately measured inference latency.

The original project concept is preserved in [project-plan.md](docs/project-plan.md). Planned features must not be presented as completed work.

## Standards and simulator references

- [ETSI TS 138 214 V16.17.0 / 3GPP TS 38.214 Release 16](https://www.etsi.org/deliver/etsi_ts/138200_138299/138214/16.17.00_60/ts_138214v161700p.pdf), especially clause 8.1.4.
- [5G-LENA NR module](https://gitlab.com/cttc-lena/nr).
- [5G-LENA NR-V2X development branch](https://gitlab.com/cttc-lena/nr/-/tree/nr-v2x-dev).


