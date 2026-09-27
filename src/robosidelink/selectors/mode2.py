"""Transparent Release 16 Mode 2-inspired resource selection."""

from __future__ import annotations

import math
import random
from dataclasses import replace

from robosidelink.config import Mode2Config
from robosidelink.models import (
    PacketStatus,
    ReservationAdvance,
    ReservationState,
    Resource,
    ResourceOffset,
    SelectionDecision,
)
from robosidelink.selectors.base import SelectionContext


def advance_reservation(
    state: ReservationState,
    *,
    keep_rng: random.Random,
    counter_rng: random.Random,
    counter_min: int,
    counter_max: int,
) -> ReservationAdvance:
    """Advance a semi-persistent reservation after one scheduled use."""
    if counter_min <= 0 or counter_max < counter_min:
        raise ValueError("invalid reselection counter bounds")
    if state.remaining_reselections > 1:
        return ReservationAdvance(
            state=replace(
                state,
                remaining_reselections=state.remaining_reselections - 1,
            ),
            requires_reselection=False,
        )
    if keep_rng.random() < state.keep_probability:
        return ReservationAdvance(
            state=replace(
                state,
                remaining_reselections=counter_rng.randint(counter_min, counter_max),
            ),
            requires_reselection=False,
        )
    return ReservationAdvance(state=None, requires_reselection=True)


class Rel16Mode2InspiredSelector:
    """Sensing-based research abstraction; not a compliant NR implementation."""

    policy_name = "rel16-mode2-inspired"

    def __init__(
        self,
        config: Mode2Config,
        *,
        choice_rng: random.Random,
        counter_rng: random.Random,
        keep_rng: random.Random,
    ) -> None:
        self._config = config
        self._choice_rng = choice_rng
        self._counter_rng = counter_rng
        self._keep_rng = keep_rng

    def select(self, context: SelectionContext) -> SelectionDecision:
        if not context.candidates:
            return self._no_feasible(context)

        reserved = self._select_reserved(context)
        if reserved is not None:
            return reserved

        evidence = (
            context.observation.evidence_by_resource
            if context.observation is not None
            else {}
        )
        threshold = self._config.initial_evidence_threshold
        required = max(
            1,
            math.ceil(
                self._config.minimum_candidate_fraction * len(context.candidates)
            ),
        )
        retained = tuple(
            candidate
            for candidate in context.candidates
            if evidence.get(candidate, 0) <= threshold
        )
        maximum_evidence = max(
            (evidence.get(candidate, 0) for candidate in context.candidates),
            default=threshold,
        )
        while len(retained) < required and threshold < maximum_evidence:
            threshold += 1
            retained = tuple(
                candidate
                for candidate in context.candidates
                if evidence.get(candidate, 0) <= threshold
            )

        if not retained:
            return self._no_feasible(context)

        resource = self._choice_rng.choice(retained)
        reservation = ReservationState(
            resource_offset=ResourceOffset(
                slot_offset=(
                    resource.slot % self._config.reservation_interval_slots
                ),
                start_subchannel=resource.start_subchannel,
                width=resource.width,
            ),
            reservation_interval_slots=self._config.reservation_interval_slots,
            remaining_reselections=self._counter_rng.randint(
                self._config.reselection_counter_min,
                self._config.reselection_counter_max,
            ),
            keep_probability=self._config.keep_probability,
        )
        return SelectionDecision(
            resource=resource,
            terminal_status=None,
            policy=self.policy_name,
            request_slot=context.request_slot,
            decision_slot=context.decision_slot,
            initial_candidate_count=len(context.candidates),
            excluded_candidate_count=len(context.candidates) - len(retained),
            retained_candidate_count=len(retained),
            relaxation_level=(
                threshold - self._config.initial_evidence_threshold
            ),
            reservation_state=reservation,
            reservation_interval_slots=reservation.reservation_interval_slots,
        )

    def _select_reserved(
        self, context: SelectionContext
    ) -> SelectionDecision | None:
        state = context.reservation_state
        if state is None:
            return None
        offset = state.resource_offset
        resource = next(
            (
                candidate
                for candidate in context.candidates
                if candidate.slot >= context.decision_slot
                and candidate.slot % state.reservation_interval_slots
                == offset.slot_offset
                and candidate.start_subchannel == offset.start_subchannel
                and candidate.width == offset.width
            ),
            None,
        )
        if resource is None:
            return None

        update = advance_reservation(
            state,
            keep_rng=self._keep_rng,
            counter_rng=self._counter_rng,
            counter_min=self._config.reselection_counter_min,
            counter_max=self._config.reselection_counter_max,
        )
        return SelectionDecision(
            resource=resource,
            terminal_status=None,
            policy=self.policy_name,
            request_slot=context.request_slot,
            decision_slot=context.decision_slot,
            initial_candidate_count=len(context.candidates),
            excluded_candidate_count=len(context.candidates) - 1,
            retained_candidate_count=1,
            reservation_state=update.state,
            reservation_interval_slots=state.reservation_interval_slots,
        )

    def _no_feasible(self, context: SelectionContext) -> SelectionDecision:
        return SelectionDecision(
            resource=None,
            terminal_status=PacketStatus.NO_FEASIBLE_RESOURCE,
            policy=self.policy_name,
            request_slot=context.request_slot,
            decision_slot=context.decision_slot,
            initial_candidate_count=len(context.candidates),
            excluded_candidate_count=len(context.candidates),
            retained_candidate_count=0,
        )
