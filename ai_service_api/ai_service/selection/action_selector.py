import random
from collections import Counter
from typing import Dict, Optional

from ai_service.offline_pipeline.categories import AnswerType, Action, Emotion, QuestionOpenness
from ai_service.models.selection import ActionSelection


class ActionSelector:
    def __init__(self,
                 reactivity_matrix: Dict[str, Dict[str, int]],
                 max_followups_in_row: int = 2,
                 random_seed: Optional[int] = None
                 ) -> None:
        self.reactivity_matrix = reactivity_matrix
        self.max_followups_in_row = max_followups_in_row
        self.random = random.Random(random_seed)


    def select(self,
               answer_type: AnswerType,
               interview_position: float,
               consecutive_followups: int,
               ) -> ActionSelection:

        if answer_type == AnswerType.NOT_ANSWER:
            return ActionSelection(
                action=Action.QUESTION ,
                reason="forced_start_of_interview",
                distribution={"question": 1.0},
            )

        if interview_position <= 0.001:
            return ActionSelection(
                action=Action.QUESTION ,
                reason="forced_start_of_interview",
                distribution={"question": 1.0},
            )

        if consecutive_followups >= self.max_followups_in_row:
            return ActionSelection(
                action=Action.TRANSITION,
                reason="forced_transition_after_followup_limit",
                distribution={"transition": 1.0},
            )

        distribution = self._get_distribution(answer_type)
        prob_distribution = self._determine_position(distribution, interview_position)

        selected = self._weighted_sample(prob_distribution)

        return ActionSelection(
            action=selected,
            reason="sampled_from_reactivity_matrix",
            distribution={k.value: v for k, v in prob_distribution.items()},
        )


    def _get_distribution(self, answer_type: AnswerType) -> Dict[Action, float]:
        row = self.reactivity_matrix.get(answer_type.value, {})

        counter = Counter()
        for reaction_type, count in row.items():
            counter[Action(reaction_type)] = count

        total = sum(counter.values())
        if total == 0:
            return {Action.TRANSITION: 1.0}

        return {act: count / total for act, count in counter.items()}


    def _determine_position(self,
                            distribution: Dict[Action, float],
                            interview_position: float,
                            ) -> Dict[Action, float]:

        probability = distribution.copy()
        if interview_position < 0.3:
            #probability[DialogueAct.OPEN_QUESTION] = probability.get(DialogueAct.OPEN_QUESTION, 0) + 0.15
            probability[Action.TRANSITION] = probability.get(Action.TRANSITION, 0) + 0.05

        if interview_position > 0.8:
            probability[Action.TRANSITION] = probability.get(Action.TRANSITION, 0) + 0.15
            probability[Action.SUMMARY] = probability.get(Action.SUMMARY, 0) + 0.10

        total = sum(probability.values())
        if total == 0:
            #return {Action.OPEN_QUESTION: 1.0}
            return {Action.TRANSITION: 1.0}

        return {k: v / total for k, v in probability.items()}


    def _weighted_sample(self, distribution: Dict[Action, float]) -> Action:
        acts = list(distribution.keys())
        weights = list(distribution.values())
        return self.random.choices(acts, weights=weights, k=1)[0]