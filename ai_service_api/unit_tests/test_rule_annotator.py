from ai_service.offline_pipeline.parsing.rule_anotator import (
    RuleAnnotator,
    normalize_text,
    word_count,
    tokenize,
    contains_marker,
    contains_any_marker,
    count_matching_markers,
    starts_with_any,
    ends_with_any,
    choose_best,
)
from ai_service.offline_pipeline.categories import (
    Action,
    AnswerType,
    Emotion,
    QuestionOpenness,
    Technique,
)


class TestNormalizeText:
    def test_lowercases(self):
        assert normalize_text("ПРИВЕТ") == "привет"

    def test_strips_whitespace(self):
        assert normalize_text("  привет  ") == "привет"

    def test_replaces_yo(self):
        assert normalize_text("ёлка") == "елка"

    def test_collapses_multiple_spaces(self):
        assert normalize_text("один  два   три") == "один два три"

    def test_removes_zero_width_chars(self):
        text = "при​вет"
        assert normalize_text(text) == "привет"


class TestWordCount:
    def test_empty_string(self):
        assert word_count("") == 0

    def test_single_word(self):
        assert word_count("слово") == 1

    def test_multiple_words(self):
        assert word_count("раз два три") == 3


class TestTokenize:
    def test_returns_lowercase_words(self):
        tokens = tokenize("Привет Мир")
        assert "привет" in tokens
        assert "мир" in tokens

    def test_strips_punctuation(self):
        tokens = tokenize("Привет, мир!")
        assert "привет" in tokens
        assert "мир" in tokens
        assert "," not in tokens

    def test_includes_numbers(self):
        tokens = tokenize("Год 2023")
        assert "2023" in tokens


class TestContainsMarker:
    def test_single_word_match(self):
        assert contains_marker("Привет всем", "привет") is True

    def test_single_word_no_match(self):
        assert contains_marker("Доброе утро", "привет") is False

    def test_multi_word_phrase_match(self):
        assert contains_marker("расскажите мне больше", "расскажите мне") is True

    def test_multi_word_phrase_no_match(self):
        assert contains_marker("расскажи мне", "расскажите мне") is False

    def test_case_insensitive(self):
        assert contains_marker("ПРИВЕТ", "привет") is True

    def test_yo_normalization(self):
        assert contains_marker("ёлка стоит", "елка") is True

    def test_returns_true_if_any_matches(self):
        assert contains_any_marker("привет друг", ["привет", "пока"]) is True

    def test_returns_false_if_none_match(self):
        assert contains_any_marker("добрый день", ["привет", "здравствуй"]) is False


class TestCountMatchingMarkers:
    def test_counts_zero(self):
        assert count_matching_markers("нет совпадений", ["привет", "пока"]) == 0

    def test_counts_one(self):
        assert count_matching_markers("привет всем", ["привет", "пока"]) == 1

    def test_counts_multiple(self):
        assert count_matching_markers("привет пока", ["привет", "пока"]) == 2


class TestStartsWithAny:
    def test_starts_with_match(self):
        assert starts_with_any("расскажите о себе", ["расскажите"]) is True

    def test_starts_with_no_match(self):
        assert starts_with_any("добрый день", ["расскажите"]) is False


class TestEndsWithAny:
    def test_ends_with_match(self):
        assert ends_with_any("это правда", ["правда"]) is True

    def test_ends_with_no_match(self):
        assert ends_with_any("добрый день", ["правда"]) is False


class TestChooseBest:
    def test_returns_best_label(self):
        scores = {"a": 5, "b": 3, "c": 1}
        assert choose_best(scores) == "a"

    def test_returns_none_below_threshold(self):
        scores = {"a": 0}
        assert choose_best(scores, threshold=1) is None

    def test_threshold_equals_score_returns_label(self):
        assert choose_best({"x": 2}, threshold=2) == "x"

    def test_threshold_above_score_returns_none(self):
        assert choose_best({"x": 1}, threshold=2) is None


class TestAnnotateAction:
    def setup_method(self):
        self.annotator = RuleAnnotator()

    def test_question_mark_yields_question(self):
        result = self.annotator.annotate_action("Как вы к этому пришли?")
        assert result == Action.QUESTION

    def test_very_short_text_yields_back_channel(self):
        result = self.annotator.annotate_action("Угу.")
        assert result in {Action.BACK_CHANNEL, Action.ACKNOWLEDGMENT}

    def test_returns_string_action(self):
        result = self.annotator.annotate_action("Расскажите подробнее о вашем опыте?")
        assert isinstance(result, Action)


class TestAnnotateQuestionOpenness:
    def setup_method(self):
        self.annotator = RuleAnnotator()

    def test_no_question_mark_is_not_a_question(self):
        result = self.annotator.annotate_question_openness("Это интересно.")
        assert result == QuestionOpenness.NOT_A_QUESTION

    def test_question_with_mark_is_not_not_a_question(self):
        result = self.annotator.annotate_question_openness("Как вы к этому пришли?")
        assert result != QuestionOpenness.NOT_A_QUESTION

    def test_returns_valid_openness(self):
        result = self.annotator.annotate_question_openness("Почему вы так решили?")
        assert isinstance(result, QuestionOpenness)


class TestAnnotateAnswerType:
    def setup_method(self):
        self.annotator = RuleAnnotator()

    def test_counter_question_short(self):
        result = self.annotator.annotate_answer_type("А зачем вам это?")
        assert result == AnswerType.COUNTER_QUESTION

    def test_long_story_with_markers(self):
        text = (
            "Это было давно. Мы тогда только начинали. "
            "Помню, как однажды зашли в офис и увидели полный хаос. "
            "Все кричали, бумаги летели, телефоны звонили. "
            "Тогда я понял, что надо менять подход."
        )
        result = self.annotator.annotate_answer_type(text)
        assert result in {
            AnswerType.STORY_WITH_EXAMPLE,
            AnswerType.EXPLANATION,
            AnswerType.UNCERTAIN,
        }

    def test_short_agreement_is_back_channel(self):
        result = self.annotator.annotate_answer_type("Да.")
        assert result in {AnswerType.BACK_CHANNEL, AnswerType.AGREEMENT}


class TestAnnotateEmotion:
    def setup_method(self):
        self.annotator = RuleAnnotator()

    def test_returns_valid_emotion(self):
        result = self.annotator.annotate_emotion("Это очень интересно.")
        assert isinstance(result, Emotion)

    def test_non_question_with_words_is_commentary_or_no_emotion(self):
        result = self.annotator.annotate_emotion("Это был сложный период.")
        assert result in {Emotion.COMMENTARY, Emotion.NO_EMOTION, Emotion.EMPATHY, Emotion.CHALLENGE}


class TestAnnotateTechniques:
    def setup_method(self):
        self.annotator = RuleAnnotator()

    def test_returns_list(self):
        result = self.annotator.annotate_techniques("Как вы к этому пришли?")
        assert isinstance(result, list)
        assert len(result) >= 1

    def test_falls_back_to_general(self):
        result = self.annotator.annotate_techniques("Ладно.")
        assert Technique.GENERAL in result

    def test_returns_valid_techniques(self):
        result = self.annotator.annotate_techniques("Почему вы так решили?")
        for t in result:
            assert isinstance(t, Technique)
