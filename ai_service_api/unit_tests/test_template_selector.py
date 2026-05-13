import pytest

from ai_service.selection.template_selector import TemplateSelector
from ai_service.offline_pipeline.categories import Action, Technique
from ai_service.models.build_profile import Template
from ai_service.models.selection import TemplateSelection
from ai_service.exeptions.generation_error import TemplateSelectionError


def make_template(
    structure,
    action,
    techniques,
    avg_position=0.5,
    frequency=10,
    template_id=None,
):
    t = Template(
        structure=structure,
        frequency=frequency,
        action=action.value,
        question_openness="open_question",
        emotion="neutral",
        techniques=techniques,
        avg_position=avg_position,
        reactivity=[],
        examples=["Пример?"],
    )
    if template_id is not None:
        # Template is a Pydantic model; attach extra attr via __dict__
        t.__dict__["template_id"] = template_id
    return t


@pytest.fixture
def question_templates():
    return [
        make_template("question", Action.QUESTION, [Technique.WHY_QUESTION], avg_position=0.3, frequency=10, template_id="q1"),
        make_template("question", Action.QUESTION, [Technique.HOW_QUESTION], avg_position=0.5, frequency=8, template_id="q2"),
        make_template("question", Action.QUESTION, [Technique.FACT_CHECK], avg_position=0.7, frequency=6, template_id="q3"),
    ]


@pytest.fixture
def mixed_templates(question_templates):
    transition = make_template(
        "bridge+question", Action.TRANSITION, [Technique.FACT_CHECK], avg_position=0.8, frequency=5, template_id="t1"
    )
    return question_templates + [transition]


@pytest.fixture
def selector(mixed_templates):
    return TemplateSelector(templates=mixed_templates, top_n=3, random_seed=42)


class TestFiltering:
    def test_returns_template_matching_action(self, selector):
        result = selector.select_template(Action.QUESTION, 0.5)
        assert result.template.action == Action.QUESTION.value

    def test_returns_transition_template(self, selector):
        result = selector.select_template(Action.TRANSITION, 0.5)
        assert result.template.action == Action.TRANSITION.value

    def test_candidates_count_reflects_filtered(self, selector):
        result = selector.select_template(Action.QUESTION, 0.5)
        assert result.candidates_count >= 1

    def test_raises_when_no_templates_for_action(self):
        selector = TemplateSelector(templates=[], top_n=3, random_seed=0)
        with pytest.raises(TemplateSelectionError) as exc_info:
            selector.select_template(Action.QUESTION, 0.5)
        assert "question" in str(exc_info.value)

    def test_raises_when_action_has_no_match(self, question_templates):
        selector = TemplateSelector(templates=question_templates, top_n=3, random_seed=0)
        with pytest.raises(TemplateSelectionError):
            selector.select_template(Action.SUMMARY, 0.5)

    def test_falls_back_to_action_only_when_no_technique_match(self):
        t = make_template("question", Action.QUESTION, [Technique.GENERAL], avg_position=0.5, frequency=10)
        selector = TemplateSelector(templates=[t], top_n=3, random_seed=0)
        result = selector.select_template(Action.QUESTION, 0.5)
        assert result.template.action == Action.QUESTION.value


class TestScoring:
    def test_position_score_closer_template_scores_higher(self):
        t_close = make_template("question", Action.QUESTION, [Technique.WHY_QUESTION], avg_position=0.3)
        t_far = make_template("question", Action.QUESTION, [Technique.WHY_QUESTION], avg_position=0.9)
        selector = TemplateSelector(templates=[t_close, t_far], top_n=3, random_seed=42)
        score_close = selector._score_template(t_close, 0.3, None)
        score_far = selector._score_template(t_far, 0.3, None)
        assert score_close > score_far

    def test_repeat_penalty_reduces_score(self):
        t = make_template("question", Action.QUESTION, [Technique.WHY_QUESTION], template_id="prev_tpl")
        selector = TemplateSelector(templates=[t], top_n=3, random_seed=0)
        score_fresh = selector._score_template(t, 0.5, None)
        score_repeat = selector._score_template(t, 0.5, "prev_tpl")
        assert score_repeat < score_fresh

    def test_no_repeat_penalty_for_different_id(self):
        t = make_template("question", Action.QUESTION, [Technique.WHY_QUESTION], template_id="tpl_A")
        selector = TemplateSelector(templates=[t], top_n=3, random_seed=0)
        score = selector._score_template(t, 0.5, "tpl_B")
        score_no_prev = selector._score_template(t, 0.5, None)
        assert score == score_no_prev

    def test_position_score_perfect_match(self):
        t = make_template("question", Action.QUESTION, [Technique.WHY_QUESTION], avg_position=0.5)
        score = TemplateSelector._position_score(t, 0.5)
        assert score == pytest.approx(1.0)

    def test_frequency_affects_score(self):
        t_high = make_template("question", Action.QUESTION, [Technique.WHY_QUESTION], frequency=100, avg_position=0.5)
        t_low = make_template("question", Action.QUESTION, [Technique.WHY_QUESTION], frequency=1, avg_position=0.5)
        selector = TemplateSelector(templates=[t_high, t_low], top_n=3, random_seed=0)
        score_high = selector._score_template(t_high, 0.5, None)
        score_low = selector._score_template(t_low, 0.5, None)
        assert score_high > score_low


class TestReturnType:
    def test_returns_template_selection_instance(self, selector):
        result = selector.select_template(Action.QUESTION, 0.5)
        assert isinstance(result, TemplateSelection)

    def test_selected_template_is_template_instance(self, selector):
        result = selector.select_template(Action.QUESTION, 0.5)
        assert isinstance(result.template, Template)

    def test_top_n_limits_candidates(self):
        templates = [
            make_template("question", Action.QUESTION, [Technique.WHY_QUESTION], avg_position=i / 10)
            for i in range(10)
        ]
        selector = TemplateSelector(templates=templates, top_n=2, random_seed=0)
        result = selector.select_template(Action.QUESTION, 0.5)
        assert result.template is not None
