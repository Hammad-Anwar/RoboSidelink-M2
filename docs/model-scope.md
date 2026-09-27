# Model Scope

RoboSidelink-M2 version 0.1 is a slot-level MAC/resource-selection research abstraction for paired cooperative robots. This document separates the behavior implemented by the simulator from mechanisms intentionally deferred to higher-fidelity work.

## System assumptions

- Time is divided into fixed-duration integer slots.
- The resource pool contains a fixed number of subchannels.
- A transmission occupies one slot and one or more contiguous subchannels.
- Adjacent robot IDs form bidirectional pairs: `0 <-> 1`, `2 <-> 3`, and so on.
- All transmitters belong to one mutual-interference domain.
- Packets are served FIFO with one active packet per transmitter.
- Traffic generation stops at the configured horizon; the simulation then drains outstanding packets.

## Included behavior

| Area | Version 0.1 behavior |
|---|---|
| Traffic | Periodic and bounded jittered-periodic arrivals |
| QoS | Absolute packet deadlines derived from generation time |
| Selection window | Inclusive future slot interval clipped to the remaining deadline |
| Resource | Slot, starting subchannel, contiguous width |
| Observation | Per-node bounded history; no sensing during own transmission slots |
| Reservation knowledge | Observable reservation intervals projected into candidates |
| Random selection | Uniform choice among deadline-feasible candidates |
| Mode 2-inspired selection | Evidence exclusion, integer relaxation, retained-set choice |
| Semi-persistent state | Reservation interval, reselection count, keep probability |
| Channel | Every overlapping same-slot transmission collides |
| Reception | Every non-overlapping transmission succeeds after one slot |
| Output | Packet, transmission, selector, metric, configuration, and metadata records |

## Abstracted behavior

### Signal sensing

The observer records deterministic occupancy evidence. It does not calculate PSCCH-RSRP or PSSCH-RSRP. A candidate receives evidence when observed activity overlaps its subchannels or an announced reservation projects onto it.

### Threshold relaxation

The Mode 2-inspired selector increases an integer evidence threshold until it retains the configured minimum candidate fraction. This makes the fallback behavior visible and testable, but it is not numerically equivalent to increasing an RSRP threshold by 3 dB.

### SCI

Reservation information is treated as perfect when a node is able to observe the slot. A collision does not currently introduce SCI decoding uncertainty.

### Processing delay

`processing_delay_ms` is converted to slots and added between selection request and decision completion. It is a sensitivity parameter. It is not a measured implementation or modem-processing value.

## Omitted behavior

- NR numerology beyond a configurable slot duration;
- PSCCH/PSSCH encoding and decoding;
- path loss, shadowing, fading, noise, SINR, MCS, BLER, and capture;
- hidden terminals and topology-dependent interference;
- mobility and factory geometry;
- retransmissions and HARQ;
- priorities beyond their presence in the packet record;
- groupcast;
- cellular scheduling and RRC procedures;
- full 3GPP conformance;
- ns-3/5G-LENA comparison;
- learning-based or SNN selection.

## Interpretation boundary

The simulator can support claims about its own resource-selection and deterministic conflict model, for example:

- how contention changes collision frequency under a declared configuration;
- how future selection windows contribute to resource-access latency;
- how the implemented sensing abstraction changes candidate sets;
- whether packets meet deadlines inside the declared model.

It cannot, without further validation, support claims about real factory-channel packet error rates, modem implementation latency, compliance, or deployed URLLC reliability.

