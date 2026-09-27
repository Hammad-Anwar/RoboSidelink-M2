# RoboSidelink-M2

**A reproducible simulator and research testbed for 5G NR Sidelink Mode 2 resource selection in cooperative robotics.**

> **Project status:** Planned / early implementation  
> **Primary technologies:** Python, C++, ns-3 / 5G-LENA  
> **Research focus:** NR Sidelink Mode 2, URLLC, cooperative robotics, resource allocation, latency, reliability, scalability

---

## 1. Project Motivation

Cooperative robots in smart factories need wireless communication with extremely low latency and very high reliability. Examples include:

- two robots coordinating a shared motion,
- robot-to-robot collision avoidance,
- cooperative manipulation,
- synchronized mobile robots or AGVs,
- small groups of robots exchanging state information.

5G NR Sidelink allows devices to communicate directly without routing every packet through the cellular infrastructure.

In **3GPP NR Sidelink Mode 2**, a user equipment autonomously selects radio resources based on sensing and resource-selection procedures.

However, conventional sensing and selection procedures may introduce delays that are difficult to reconcile with aggressive industrial URLLC packet-delay budgets.

This project studies that problem in a reproducible simulation environment.

The initial goal is not to reproduce every detail of the full 3GPP physical layer. Instead, the project will build a transparent research simulator that captures the resource-selection behavior relevant to latency, collisions, packet deadlines, reliability, and scalability.

The simulator can later be connected to or validated against **ns-3 / 5G-LENA NR Sidelink**.

---

## 2. Research Question

### Main question

**How well can autonomous NR Sidelink Mode 2 resource selection satisfy very low-latency and high-reliability requirements for cooperative robotic communication?**

### Sub-questions

1. How much latency is introduced by sensing-window-based resource selection?
2. How frequently do autonomous users select the same radio resource?
3. How do collisions change as the number of robot pairs or group members increases?
4. How does traffic periodicity affect Mode 2 resource selection?
5. What happens when packet deadlines are between roughly 1–3 ms?
6. Can shorter observation windows achieve acceptable resource-selection accuracy?
7. Can instantaneous channel-observation mechanisms outperform conventional sensing windows?
8. Can event-driven or learning-based resource-selection approaches eventually reduce decision latency?

---

## 3. Project Objectives

The project will be developed in stages.

### Phase 1 — Lightweight Python simulator

Build a transparent discrete-event simulator for:

- cooperative robot nodes,
- periodic and event-driven packet generation,
- time-frequency radio resources,
- autonomous resource selection,
- sensing windows,
- resource exclusion,
- resource collisions,
- retransmission options,
- packet deadlines,
- packet success/failure,
- unicast communication,
- small-group groupcast communication.

### Phase 2 — Simplified Rel.16 Mode 2 baseline

Implement a documented abstraction of the Rel.16 Mode 2 sensing-based resource-selection process.

The baseline should include:

- sensing history,
- candidate-resource generation,
- exclusion of occupied resources,
- randomized selection from valid candidates,
- configurable reservation duration,
- configurable sensing-window length,
- configurable selection-window length.

The abstraction must clearly document which 3GPP mechanisms are modeled and which are intentionally simplified.

### Phase 3 — Alternative resource-selection mechanisms

Evaluate faster alternatives such as:

- short sensing windows,
- most-recent-slot observation,
- instantaneous channel observation,
- probabilistic resource occupancy estimation,
- greedy least-occupied-resource selection,
- collision-history-aware selection,
- randomized low-overhead selection.

### Phase 4 — ns-3 / 5G-LENA comparison

Reproduce selected scenarios in ns-3 / 5G-LENA where practical.

Use the Python simulator for:

- rapid experiments,
- algorithm development,
- visualization,
- parameter sweeps.

Use ns-3 / 5G-LENA for:

- higher-fidelity networking experiments,
- comparison with an established 5G NR simulator,
- validation of major conclusions.

### Optional Phase 5 — SNN-based selector

Explore a **Spiking Neural Network (SNN)** or other event-driven inference mechanism as an optional extension.

Possible inputs:

- recent channel occupancy,
- resource collision history,
- queue age,
- remaining packet deadline,
- neighboring reservations,
- recent received signal indicators.

Possible output:

- selected resource index,
- ranked resource candidates,
- probability of collision for each resource.

The important research question is not only prediction accuracy but also:

**Can inference finish inside the MAC-layer decision budget?**

---

## 4. Recommended Project Name

### Preferred name

# **RoboSidelink-M2**

Why:

- short,
- descriptive,
- directly references robotics,
- directly references Sidelink Mode 2,
- suitable for a GitHub repository,
- suitable for mentioning on a CV or thesis application.

Recommended repository name:

```text
robosidelink-m2
```

### Other good options

| Name | Style |
|---|---|
| **RoboSidelink-M2** | Professional and research-oriented |
| **SidelinkForge** | More memorable / project-like |
| **RobotSL-URLLC** | Very technical |
| **Mode2FactorySim** | Explicit factory focus |
| **CoopSL-Sim** | Cooperative Sidelink simulator |
| **SidelinkLab** | Broad, extensible research toolkit |
| **RoboURLLC-SL** | URLLC-focused |
| **FactorySidelink** | Smart-factory focused |

---

## 5. Initial Scope

The first version should deliberately avoid unnecessary PHY complexity.

### Include

- discrete simulation time,
- configurable slot duration,
- resource pool,
- robot nodes,
- packet generation,
- resource reservations,
- sensing history,
- autonomous resource selection,
- collisions,
- packet deadlines,
- unicast,
- groupcast,
- metrics,
- reproducible random seeds.

### Do not initially include

- complete NR PHY implementation,
- beamforming,
- detailed antenna models,
- HARQ implementation matching every 3GPP detail,
- complete RRC procedures,
- mobility handover,
- cellular scheduling.

These can be added later if they become necessary.

---

## 6. System Model

Assume a factory floor containing multiple cooperative robotic devices.

Each device periodically or asynchronously generates control packets.

A packet is characterized by:

```text
packet_id
source
destination/group
generation_time
deadline
payload_size
priority
```

Each transmitter independently selects a Sidelink resource.

A resource can be represented as:

```text
(time_slot, subchannel)
```

Example resource grid:

```text
                Frequency
            SC0 SC1 SC2 SC3
Slot 0       .   .   .   .
Slot 1       .   .   .   .
Slot 2       .   .   .   .
Slot 3       .   .   .   .
```

If two interfering transmitters choose the same resource, a collision may occur.

The first implementation may use a deterministic collision model:

```text
same time slot
+ same subchannel
+ mutual interference
= collision
```

Later, the collision model can be replaced by an SINR-based success model.

---

## 7. Suggested Simulator Architecture

```text
+--------------------------------------------------+
|                Experiment Runner                 |
+--------------------------------------------------+
                     |
                     v
+--------------------------------------------------+
|                 Scenario Config                  |
| nodes, traffic, resources, deadlines, seed       |
+--------------------------------------------------+
                     |
                     v
+------------------ Simulation --------------------+
|                                                  |
|  +-------------+     +----------------------+    |
|  | Robot Nodes | --> | Resource Selector    |    |
|  +-------------+     +----------------------+    |
|         |                      |                  |
|         v                      v                  |
|  +-------------+     +----------------------+    |
|  | Packet Queue|     | Sensing History      |    |
|  +-------------+     +----------------------+    |
|         |                      |                  |
|         +----------+-----------+                  |
|                    v                              |
|            +---------------+                     |
|            | Resource Pool |                     |
|            +---------------+                     |
|                    |                              |
|                    v                              |
|            +---------------+                     |
|            | Channel Model |                     |
|            +---------------+                     |
|                    |                              |
|                    v                              |
|            +---------------+                     |
|            | Metrics Logger|                     |
|            +---------------+                     |
+--------------------------------------------------+
```

---

## 8. Core Python Classes

A clean first implementation could use the following components.

### `RobotNode`

Responsibilities:

- generate packets,
- maintain transmit queue,
- maintain sensing history,
- request resource selection,
- transmit packets,
- track deadlines.

### `Packet`

Fields:

```python
packet_id
source_id
destination_ids
generation_time
deadline
payload_size
priority
```

### `Resource`

Fields:

```python
slot
subchannel
reserved_by
reservation_expiry
```

### `ResourcePool`

Responsibilities:

- maintain time-frequency resources,
- expose available candidates,
- record occupancy,
- detect conflicting allocations.

### `ChannelObserver`

Responsibilities:

- collect observations,
- maintain sensing history,
- estimate occupied resources.

Different implementations can include:

```text
LongWindowObserver
ShortWindowObserver
InstantObserver
```

### `ResourceSelector`

Base interface:

```python
select_resource(node, packet, observation, candidate_resources)
```

Implementations:

```text
RandomSelector
Mode2BaselineSelector
ShortWindowSelector
InstantObservationSelector
CollisionAwareSelector
SNNSelector
```

### `ChannelModel`

Version 1:

```text
collision => packet failure
no collision => packet success
```

Version 2:

SINR-based packet reception.

### `MetricsCollector`

Collect:

- generated packets,
- transmitted packets,
- successful packets,
- failed packets,
- deadline misses,
- collisions,
- selection delays,
- end-to-end delays,
- utilization.

---

## 9. Baseline Algorithms

### Baseline A — Random Resource Selection

Select uniformly from all candidate resources.

Purpose:

- sanity check,
- lower-complexity reference.

Pseudo-code:

```text
candidate_resources = get_resources_in_selection_window()

selected = random(candidate_resources)
```

---

### Baseline B — Simplified Rel.16 Mode 2

Conceptual flow:

```text
1. Observe previous channel usage.
2. Build a list of candidate future resources.
3. Exclude resources considered occupied.
4. Apply selection thresholds.
5. Randomly select from the remaining candidate resources.
6. Reserve the resource for one or more packet transmissions.
```

Pseudo-code:

```python
history = observer.get_history(sensing_window)

candidates = resource_pool.future_resources(selection_window)

filtered = []

for resource in candidates:
    if not history.is_likely_occupied(resource):
        filtered.append(resource)

if len(filtered) < minimum_candidate_count:
    filtered = relax_exclusion_threshold(candidates)

selected = random.choice(filtered)
```

---

## 10. Proposed Alternative Algorithms

### A. Short-window sensing

Use only the last:

```text
1 ms
2 ms
5 ms
```

instead of a longer historical window.

Research question:

> At what point does reducing sensing history materially hurt collision avoidance?

---

### B. Instantaneous observation

Only observe the most recent channel state.

Algorithm:

```text
observe current/recent slot
exclude currently active/reserved resources
select immediately
```

Goal:

Reduce resource-selection latency.

---

### C. Least-occupied resource

Maintain a resource occupancy score.

```text
score(resource) =
    observed_occupancy +
    recent_collision_penalty
```

Select the lowest-score resource.

---

### D. Deadline-aware selection

If a packet has very little remaining delay budget, prefer the earliest feasible resource.

Example score:

```text
score =
    alpha * predicted_collision_probability
  + beta  * waiting_time
  + gamma * deadline_risk
```

---

### E. Collision-history-aware selector

Each node maintains:

```text
resource -> recent collision frequency
```

Avoid repeatedly problematic resources.

---

### F. Optional SNN selector

Input spike representation may encode:

```text
resource occupancy
collision events
packet arrivals
remaining deadline
neighbor activity
```

Output neuron:

```text
one neuron per candidate resource
```

Selected resource:

```text
first/highest output spike
```

Evaluation must include:

- prediction accuracy,
- collision reduction,
- inference latency,
- CPU/GPU inference time,
- memory footprint.

---

## 11. Traffic Models

Implement at least three traffic types.

### Periodic control traffic

Example:

```text
packet every 1 ms
packet every 2 ms
packet every 5 ms
```

### Jittered periodic traffic

```text
period + random jitter
```

### Event-driven burst traffic

Useful for:

- emergency stop,
- coordinated motion change,
- collision avoidance,
- robot task transitions.

---

## 12. Communication Modes

### Unicast

Typical scenario:

```text
Robot A <----> Robot B
```

Useful for:

- paired cooperative manipulation,
- leader/follower motion.

### Groupcast

Typical scenario:

```text
Robot A
  | \
  |  \
  v   v
Robot B Robot C
```

Useful for:

- coordinated robot teams,
- AGV platoons,
- synchronized cells.

---

## 13. Important Parameters

All parameters should live in YAML/JSON configuration files.

Example:

```yaml
simulation:
  duration_ms: 10000
  seed: 42

radio:
  slot_duration_ms: 0.25
  num_subchannels: 8

traffic:
  type: periodic
  period_ms: 2
  packet_size_bytes: 64

qos:
  packet_deadline_ms: 3

mode2:
  sensing_window_ms: 100
  selection_window_ms: 3

scenario:
  num_robot_pairs: 4
  communication: unicast
```

This makes experiments reproducible.

---

## 14. Core Metrics

### Packet Delivery Ratio

```text
PDR =
successful packets / generated packets
```

### Packet Deadline Success Ratio

```text
PDSR =
packets delivered before deadline / generated packets
```

This should be one of the most important metrics.

### Collision Probability

```text
collision probability =
collided transmissions / total transmissions
```

### Resource Selection Latency

```text
selection latency =
resource decision time - packet arrival time
```

### End-to-End Delay

```text
packet reception time - packet generation time
```

Report:

- mean,
- median,
- 95th percentile,
- 99th percentile,
- maximum.

### Deadline Miss Ratio

```text
missed deadlines / generated packets
```

### Resource Utilization

```text
used resources / total resources
```

### Scalability

Measure performance while increasing:

```text
number of robot pairs
number of nodes
traffic load
group size
```

---

## 15. Experiment Plan

### Experiment 1 — Baseline validation

Compare:

```text
Random selection
vs.
Simplified Rel.16 Mode 2
```

Sweep:

```text
2
4
8
16
32 nodes
```

Measure:

- PDR,
- collision probability,
- delay.

---

### Experiment 2 — Sensing-window impact

Sweep sensing windows:

```text
1 ms
2 ms
5 ms
10 ms
20 ms
50 ms
100 ms
```

Measure:

- collision probability,
- decision latency,
- packet deadline success ratio.

Main plot:

```text
sensing window length
vs.
deadline success probability
```

---

### Experiment 3 — Packet deadline sensitivity

Deadlines:

```text
1 ms
2 ms
3 ms
5 ms
10 ms
```

Determine when the baseline becomes unsuitable.

---

### Experiment 4 — Network density

Increase cooperative robot population.

Example:

```text
1 pair
2 pairs
4 pairs
8 pairs
16 pairs
```

Measure scalability.

---

### Experiment 5 — Traffic load

Change packet periodicity:

```text
1 ms
2 ms
5 ms
10 ms
```

Evaluate congestion.

---

### Experiment 6 — Instantaneous observation

Compare:

```text
Rel.16-inspired baseline
Short sensing window
Instant observation
```

Measure the reliability/latency trade-off.

---

### Experiment 7 — Unicast vs groupcast

Compare:

```text
pairwise cooperative robots
vs.
small groups of 3–8 robots
```

---

### Experiment 8 — Optional learning-based selector

Compare:

```text
Mode2 baseline
heuristic selector
SNN selector
```

Measure:

- PDR,
- deadline success,
- collision rate,
- inference latency.

---

## 16. Suggested Repository Structure

```text
robosidelink-m2/
│
├── README.md
├── LICENSE
├── pyproject.toml
├── requirements.txt
│
├── configs/
│   ├── baseline.yaml
│   ├── short_window.yaml
│   ├── instant_observation.yaml
│   └── scalability.yaml
│
├── src/
│   └── robosidelink/
│       ├── __init__.py
│       ├── simulator.py
│       ├── node.py
│       ├── packet.py
│       ├── resource.py
│       ├── resource_pool.py
│       ├── channel.py
│       ├── traffic.py
│       ├── metrics.py
│       │
│       ├── observers/
│       │   ├── base.py
│       │   ├── long_window.py
│       │   ├── short_window.py
│       │   └── instant.py
│       │
│       └── selectors/
│           ├── base.py
│           ├── random_selector.py
│           ├── mode2_baseline.py
│           ├── deadline_aware.py
│           ├── collision_aware.py
│           └── snn_selector.py
│
├── experiments/
│   ├── run_baseline.py
│   ├── sensing_window_sweep.py
│   ├── deadline_sweep.py
│   ├── density_sweep.py
│   └── groupcast_sweep.py
│
├── notebooks/
│   ├── 01_baseline_analysis.ipynb
│   ├── 02_sensing_window.ipynb
│   └── 03_scalability.ipynb
│
├── results/
│   └── .gitkeep
│
├── plots/
│   └── .gitkeep
│
├── tests/
│   ├── test_resource_pool.py
│   ├── test_collisions.py
│   ├── test_deadlines.py
│   └── test_mode2_selector.py
│
├── ns3/
│   ├── README.md
│   └── scenarios/
│
└── docs/
    ├── system_model.md
    ├── mode2_baseline.md
    ├── assumptions.md
    └── experiment_design.md
```

---

## 17. Command-Line Interface

The simulator should eventually support:

```bash
python -m robosidelink \
    --config configs/baseline.yaml
```

Parameter override example:

```bash
python -m robosidelink \
    --config configs/baseline.yaml \
    --nodes 16 \
    --deadline-ms 3 \
    --seed 42
```

Experiment sweep:

```bash
python experiments/sensing_window_sweep.py
```

---

## 18. Output Format

Each simulation should produce machine-readable results.

Example CSV:

```text
run_id,seed,nodes,sensing_window_ms,pdr,deadline_success,collision_rate,p95_delay_ms
1,42,8,100,0.999,0.972,0.014,2.40
2,43,8,10,0.997,0.988,0.019,1.65
3,44,8,2,0.992,0.995,0.027,0.91
```

Also save experiment metadata:

```json
{
  "git_commit": "...",
  "seed": 42,
  "config": "baseline.yaml",
  "timestamp": "...",
  "simulator_version": "0.1.0"
}
```

---

## 19. Reproducibility Requirements

Every published graph should be reproducible using:

```text
configuration file
+
random seed
+
code version
```

Recommended workflow:

```bash
git clone ...
pip install -e .
python experiments/sensing_window_sweep.py
python scripts/plot_results.py
```

---

## 20. Testing Strategy

Write tests before adding advanced features.

Important tests:

### Resource collision

```text
two nodes
same resource
=> collision
```

### Independent resources

```text
two nodes
different resources
=> success
```

### Deadline expiration

```text
packet transmitted after deadline
=> deadline miss
```

### Sensing exclusion

```text
observed occupied resource
=> not selected by baseline
```

### Reproducibility

```text
same seed + same config
=> same result
```

---

## 21. Development Roadmap

### Milestone 1 — Minimal simulator

Implement:

- simulation clock,
- resource pool,
- nodes,
- packets,
- random resource selection,
- collisions,
- CSV metrics.

Deliverable:

```text
2–10 nodes sharing radio resources
```

---

### Milestone 2 — Traffic and deadlines

Add:

- periodic packets,
- configurable deadlines,
- packet queues,
- latency statistics.

Deliverable:

```text
PDR + deadline-success graphs
```

---

### Milestone 3 — Mode 2 inspired baseline

Add:

- sensing history,
- candidate filtering,
- resource reservation,
- selection window.

Deliverable:

```text
Random vs Mode2 baseline comparison
```

---

### Milestone 4 — Experiment framework

Add:

- YAML configs,
- parameter sweeps,
- multiple random seeds,
- automated plots.

Deliverable:

```text
reproducible experiment pipeline
```

---

### Milestone 5 — URLLC study

Run:

- 1–3 ms deadlines,
- sensing-window sweep,
- robot-density sweep.

Deliverable:

```text
evidence showing where baseline resource selection struggles
```

---

### Milestone 6 — Fast resource selection

Implement:

- short-window sensing,
- instantaneous observation,
- deadline-aware selector.

Deliverable:

```text
latency-reliability comparison
```

---

### Milestone 7 — ns-3 / 5G-LENA

Implement equivalent selected scenarios.

Deliverable:

```text
Python-model vs ns-3 comparison
```

---

### Milestone 8 — Optional SNN

Prototype event-driven inference.

Deliverable:

```text
SNN vs heuristic vs baseline
```

---

## 22. Recommended First Four Weeks

### Week 1

Build:

```text
Resource
ResourcePool
Packet
RobotNode
Simulation
```

Goal:

Two nodes can transmit and collide.

### Week 2

Add:

```text
periodic traffic
deadlines
metrics
CSV output
```

Produce first plots:

```text
number of nodes vs collision rate
number of nodes vs PDR
```

### Week 3

Implement:

```text
sensing history
candidate resource filtering
simplified Mode 2 baseline
```

Produce:

```text
random vs Mode2
```

### Week 4

Run sensing-window sweep.

Produce:

```text
sensing window vs collision rate
sensing window vs deadline success
sensing window vs latency
```

After these four weeks, the repository should already be strong enough to discuss in a thesis interview.

---

## 23. Recommended First GitHub Issues

Create these issues immediately:

```text
#1 Define discrete-event simulation clock
#2 Implement Resource and ResourcePool
#3 Implement Packet model
#4 Implement RobotNode
#5 Implement periodic traffic generator
#6 Implement deterministic collision model
#7 Implement MetricsCollector
#8 Add YAML configuration loader
#9 Implement random resource selector
#10 Implement sensing history
#11 Implement simplified Mode 2 selector
#12 Add sensing-window experiment
#13 Add density sweep
#14 Add deadline sweep
#15 Create plotting pipeline
```

---

## 24. First Minimum Viable Experiment

The first meaningful experiment should be intentionally simple.

### Scenario

```text
8 robots
4 subchannels
0.25 ms slots
periodic traffic every 2 ms
3 ms packet deadline
10 second simulation
```

Compare:

```text
RandomSelector
Mode2BaselineSelector
```

Sweep:

```text
2, 4, 8, 16, 32 robots
```

Collect:

```text
PDR
collision rate
deadline success
mean delay
95th percentile delay
```

This experiment gives an immediate end-to-end demonstration of the simulator.

---

## 25. Example Research Hypotheses

Possible hypotheses to test:

### H1

Long sensing windows improve collision avoidance but are poorly suited to very small packet-delay budgets.

### H2

A short-window observation mechanism can achieve similar reliability with lower resource-selection latency in moderately loaded factory scenarios.

### H3

As cooperative robot density increases, stale sensing information becomes less useful because channel occupancy changes faster.

### H4

Deadline-aware resource selection improves deadline success even if raw collision probability does not significantly improve.

### H5

Instantaneous observation is most useful in low-to-medium-density scenarios but becomes less reliable under high contention.

### H6

Event-driven inference can become attractive when its inference latency is significantly smaller than the sensing/decision delay it replaces.

---

## 26. Plots Worth Publishing

Recommended figures:

```text
PDR vs number of robots
Deadline success vs number of robots
Collision rate vs number of robots
P95 latency vs number of robots

Collision rate vs sensing-window duration
Deadline success vs sensing-window duration
Selection latency vs sensing-window duration

PDR vs traffic period
Deadline success vs packet deadline

Unicast vs groupcast reliability

Mode2 baseline vs short-window vs instant observation
```

---

## 27. What Makes This Project Strong for a Thesis Application

The project demonstrates several skills simultaneously:

- wireless communication fundamentals,
- 5G NR Sidelink understanding,
- MAC-layer resource allocation,
- URLLC reasoning,
- discrete-event simulation,
- Python software engineering,
- C++ / ns-3 extension potential,
- experiment design,
- statistical evaluation,
- reproducibility,
- performance visualization.

More importantly, it directly produces research questions rather than only software.

---

## 28. CV Description

Once the first baseline implementation works, a stronger CV version could be:

> **RoboSidelink-M2 — NR Sidelink Mode 2 Resource Selection Simulator**  
> Python, ns-3/5G-LENA, 5G NR Sidelink, performance analysis  
> - Developed a reproducible simulator for autonomous NR Sidelink resource selection in cooperative robotic scenarios with configurable sensing windows, periodic traffic, packet deadlines, and resource collisions.  
> - Evaluated resource-selection latency, packet delivery reliability, collision probability, and scalability under varying robot densities and URLLC deadlines.  
> - Implemented and compared a simplified Rel.16 Mode 2 baseline with low-latency sensing and resource-selection strategies.

Do not claim ns-3/5G-LENA implementation until that part has actually been completed.

---

## 29. Possible Thesis-Level Extension

A strong thesis version can evolve into the following study:

```text
                    ┌─────────────────────────┐
                    │ Rel.16 Mode 2 Baseline  │
                    └────────────┬────────────┘
                                 │
                                 v
                    ┌─────────────────────────┐
                    │ Identify latency limits │
                    └────────────┬────────────┘
                                 │
             ┌───────────────────┼───────────────────┐
             v                   v                   v
    ┌────────────────┐  ┌────────────────┐  ┌────────────────┐
    │ Short sensing  │  │ Instantaneous  │  │ Event-driven   │
    │ window         │  │ observation    │  │ SNN inference  │
    └───────┬────────┘  └───────┬────────┘  └───────┬────────┘
            │                   │                   │
            └───────────────────┼───────────────────┘
                                v
                    ┌─────────────────────────┐
                    │ URLLC benchmark        │
                    │ latency + reliability  │
                    └────────────┬────────────┘
                                 │
                                 v
                    ┌─────────────────────────┐
                    │ Unicast / Groupcast    │
                    │ scalability analysis   │
                    └─────────────────────────┘
```

This structure aligns well with a research thesis because it progresses from:

```text
problem characterization
→ baseline
→ proposed mechanisms
→ evaluation
→ scalability
```

---

## 30. Recommended Starting Point

Do **not** begin with ns-3 or SNNs.

Start with this sequence:

```text
1. Python time-frequency resource simulator
2. Collision model
3. Packet deadlines
4. Random selector
5. Mode 2-inspired selector
6. Sensing-window experiments
7. Low-latency alternative
8. ns-3 validation
9. SNN only if time permits
```

The first important milestone is:

> **Produce one plot that shows how sensing-window length affects packet deadline success for cooperative robots.**

That result will immediately connect the software project to the research question.

---

## 31. License

A permissive license such as **MIT** or **Apache-2.0** is suitable for an open research simulator.

---

## 32. Disclaimer

This project initially implements a research-oriented abstraction of NR Sidelink Mode 2.

It should not claim full 3GPP compliance unless every relevant procedure and parameter has been independently verified against the applicable specifications.

---

## 33. Final Project Goal

The final repository should allow someone to run:

```bash
git clone <repository>
cd robosidelink-m2

pip install -e .

python experiments/sensing_window_sweep.py
```

and automatically reproduce a result showing:

```text
how autonomous resource selection,
sensing-window duration,
network density,
and packet deadlines
affect cooperative-robot Sidelink reliability.
```

That is the core scientific story of **RoboSidelink-M2**.
