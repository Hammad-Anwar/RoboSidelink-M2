"""Uniform random selection from deadline-feasible candidates."""

import random

from robosidelink.models import PacketStatus, SelectionDecision
from robosidelink.selectors.base import SelectionContext


class RandomSelector:
    policy_name = "random"

    def __init__(self, rng: random.Random) -> None:
        self._rng = rng

    def select(self, context: SelectionContext) -> SelectionDecision:
        candidate_count = len(context.candidates)
        if not context.candidates:
            return SelectionDecision(
                resource=None,
                terminal_status=PacketStatus.NO_FEASIBLE_RESOURCE,
                policy=self.policy_name,
                request_slot=context.request_slot,
                decision_slot=context.decision_slot,
                initial_candidate_count=0,
                excluded_candidate_count=0,
                retained_candidate_count=0,
            )

        return SelectionDecision(
            resource=self._rng.choice(context.candidates),
            terminal_status=None,
            policy=self.policy_name,
            request_slot=context.request_slot,
            decision_slot=context.decision_slot,
            initial_candidate_count=candidate_count,
            excluded_candidate_count=0,
            retained_candidate_count=candidate_count,
        )
