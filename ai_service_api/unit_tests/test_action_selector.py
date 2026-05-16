import pytest
from collections import Counter

from ai_service.selection.action_selector import ActionSelector
from ai_service.offline_pipeline.categories import Action, AnswerType
from ai_service.models.selection import ActionSelection


@pytest.fixture
def selector(reactivity_matrix):
    return ActionSelector(
        reactivity_matrix=reactivity_matrix,
        max_followups_in_row=2,
        random_seed=42,
    )


class TestForcedBehaviors:
    def test_not_answer_forces_question(self, selector):
        result = selector.select(
            answer_type=AnswerType.NOT_ANSWER,
            interview_position=0.5,
            consecutive_followups=0,
        )
        assert result.action == Action.QUESTION
        assert result.reason == "forced_start_of_interview"

    def test_position_zero_forces_question(self, selector):
        result = selector.select(
            answer_type=AnswerType.EXPLANATION,
            interview_position=0.0,
            consecutive_followups=0,
        )
        assert result.action == Action.QUESTION
        assert result.reason == "forced_start_of_interview"

    def test_position_near_zero_forces_question(self, selector):
        result = selector.select(
            answer_type=AnswerType.EXPLANATION,
            interview_position=0.001,
            consecutive_followups=0,
        )
        assert result.action == Action.QUESTION
        assert result.reason == "forced_start_of_interview"

    def test_position_just_above_threshold_does_not_force(self, selector):
        result = selector.select(
            answer_type=AnswerType.EXPLANATION,
            interview_position=0.002,
            consecutive_followups=0,
        )
        assert result.reason != "forced_start_of_interview"

    def test_max_followups_forces_transition(self, selector):
        result = selector.select(
            answer_type=AnswerType.EXPLANATION,
            interview_position=0.5,
            consecutive_followups=2,
        )
        assert result.action == Action.TRANSITION
        assert result.reason == "forced_transition_after_followup_limit"

    def test_exceeding_max_followups_forces_transition(self, selector):
        result = selector.select(
            answer_type=AnswerType.EXPLANATION,
            interview_position=0.5,
            consecutive_followups=10,
        )
        assert result.action == Action.TRANSITION

    def test_below_max_followups_samples_normally(self, selector):
        result = selector.select(
            answer_type=AnswerType.EXPLANATION,
            interview_position=0.5,
            consecutive_followups=1,
        )
        assert result.reason == "sampled_from_reactivity_matrix"


class TestDistributionBuilding:
    def test_get_distribution_sums_to_one(self, selector):
        dist = selector._get_distribution(AnswerType.EXPLANATION)
        total = sum(dist.values())
        assert abs(total - 1.0) < 1e-9

    def test_get_distribution_unknown_answer_type_returns_transition(self, selector):
        dist = selector._get_distribution(AnswerType.UNCERTAIN)
        assert dist == {Action.TRANSITION: 1.0}

    def test_get_distribution_proportions(self, selector):
        dist = selector._get_distribution(AnswerType.EXPLANATION)
        total_counts = 5 + 2 + 1
        assert abs(dist[Action.QUESTION] - 5 / total_counts) < 1e-9
        assert abs(dist[Action.TRANSITION] - 2 / total_counts) < 1e-9
        assert abs(dist[Action.CLARIFICATION] - 1 / total_counts) < 1e-9


class TestPositionAdjustments:
    def test_early_position_boosts_transition(self, selector):
        base_dist = selector._get_distribution(AnswerType.EXPLANATION)
        adjusted = selector._determine_position(base_dist, 0.1)
        assert adjusted[Action.TRANSITION] > base_dist.get(Action.TRANSITION, 0)

    def test_late_position_boosts_transition_and_summary(self, selector):
        base_dist = {Action.QUESTION: 0.7, Action.TRANSITION: 0.3}
        adjusted = selector._determine_position(base_dist, 0.9)
        assert adjusted[Action.TRANSITION] > 0.3
        assert Action.SUMMARY in adjusted

    def test_mid_position_unchanged_boost(self, selector):
        base_dist = {Action.QUESTION: 0.7, Action.TRANSITION: 0.3}
        adjusted = selector._determine_position(base_dist, 0.5)
        total = sum(adjusted.values())
        assert abs(total - 1.0) < 1e-9

    def test_adjusted_distribution_sums_to_one(self, selector):
        base_dist = selector._get_distribution(AnswerType.AGREEMENT)
        for position in [0.0, 0.1, 0.5, 0.85, 1.0]:
            adjusted = selector._determine_position(base_dist, position)
            assert abs(sum(adjusted.values()) - 1.0) < 1e-9

    def test_empty_distribution_returns_transition(self, selector):
        result = selector._determine_position({}, 0.5)
        assert result == {Action.TRANSITION: 1.0}


class TestWeightedSample:
    def test_returns_valid_action(self, selector):
        dist = {Action.QUESTION: 0.5, Action.TRANSITION: 0.3, Action.CLARIFICATION: 0.2}
        for _ in range(20):
            result = selector._weighted_sample(dist)
            assert result in {Action.QUESTION, Action.TRANSITION, Action.CLARIFICATION}

    def test_respects_weights_statistically(self):
        selector = ActionSelector(reactivity_matrix={}, random_seed=99)
        dist = {Action.QUESTION: 0.9, Action.TRANSITION: 0.1}
        counts = Counter(selector._weighted_sample(dist) for _ in range(1000))
        assert counts[Action.QUESTION] > counts[Action.TRANSITION]


class TestSelectReturnType:
    def test_select_returns_action_selection(self, selector):
        result = selector.select(
            answer_type=AnswerType.EXPLANATION,
            interview_position=0.5,
            consecutive_followups=0,
        )
        assert isinstance(result, ActionSelection)
        assert isinstance(result.action, str)
        assert isinstance(result.reason, str)
        assert isinstance(result.distribution, dict)

    def test_distribution_in_result_sums_to_one(self, selector):
        result = selector.select(
            answer_type=AnswerType.AGREEMENT,
            interview_position=0.5,
            consecutive_followups=0,
        )
        total = sum(result.distribution.values())
        assert abs(total - 1.0) < 1e-6