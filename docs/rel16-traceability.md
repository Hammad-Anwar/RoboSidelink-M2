# Release 16 Mode 2 Traceability

The normative reference used for the version 0.1 baseline is [ETSI TS 138 214 V16.17.0](https://www.etsi.org/deliver/etsi_ts/138200_138299/138214/16.17.00_60/ts_138214v161700p.pdf), which transposes 3GPP TS 38.214 version 16.17.0 Release 16. The main reference is clause 8.1.4, UE procedure for sidelink resource selection.

The implemented class is deliberately named `Rel16Mode2InspiredSelector`. It must not be described as a compliant implementation.

## Concept mapping

| Rel.16 concept | Implementation | Fidelity |
|---|---|---|
| Selection invocation at slot `n` | A queued head-of-line packet requests selection at an integer slot | Modeled |
| Future interval `[n + T1, n + T2]` | Inclusive candidate interval configured in slots | Modeled |
| Remaining packet delay budget | Candidate end is clipped to the latest slot completing by the deadline | Modeled |
| Candidate single-slot resource | Slot plus configurable contiguous subchannel width | Modeled |
| Historical sensing window | Per-node history before the decision slot | Modeled |
| Own-transmission sensing exclusion | A node receives no observations for a slot in which it transmitted | Modeled |
| Reservation interval | Observed periodic reservations project into future candidates | Modeled |
| Candidate exclusion | Candidates above an evidence threshold are excluded | Abstracted |
| RSRP threshold | Replaced by a deterministic integer occupancy-evidence threshold | Abstracted |
| Threshold relaxation | Integer threshold increases until the minimum candidate fraction remains | Abstracted |
| Random selection from retained set | Uniform seeded choice | Modeled |
| Resource reselection counter | Inclusive configured counter range | Modeled |
| Probability of keeping resource | Independent seeded keep decision | Modeled |
| SCI decoding | Reservation information is perfect when observable | Simplified |
| PSCCH/PSSCH RSRP | Not calculated | Omitted |
| PHY reception and BLER | Deterministic resource-overlap outcome | Omitted |
| HARQ | One attempt per packet | Omitted |
| Full Mode 2 configuration/procedure set | Not attempted | Omitted |

## Timing interpretation

The specification defines the sensing window as past slots monitored by the UE. RoboSidelink-M2 therefore does not add the sensing-window duration directly to every packet's selection latency.

The simulator records four separate quantities:

1. packet queueing before selection is requested;
2. configurable decision processing;
3. waiting for the selected future resource;
4. one-slot transmission and reception completion.

This separation prevents a long history length from being incorrectly presented as an equal amount of per-packet waiting time.

## Evidence score

For each candidate resource, the observer counts relevant historical or projected occupancy evidence whose subchannels overlap the candidate. The initial evidence threshold is configured. If the retained set is smaller than `minimum_candidate_fraction`, the threshold is increased by one integer level until enough candidates remain or all observed levels have been admitted.

This mechanism preserves the research role of exclusion and relaxation while remaining explicit about its departure from RSRP-based processing.

## Validation roadmap

Before describing the simulator as a closer Mode 2 reproduction, future work must add or validate:

- exact sidelink resource-pool indexing and standard parameter ranges;
- priority-dependent RSRP thresholds;
- SCI decoding and reservation semantics;
- standard reselection-counter rules for the selected resource reservation interval;
- partial sensing and pre-emption where applicable;
- PHY/MAC timing against an identified ns-3/5G-LENA NR-V2X revision;
- scenario-level comparison using identical traffic, pool, and packet-delay inputs.

