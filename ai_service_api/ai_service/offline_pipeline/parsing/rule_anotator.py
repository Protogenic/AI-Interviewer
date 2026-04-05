import re
import logging

from ai_service.offline_pipeline.categories import Action, QuestionOpenness, Emotion, Technique, AnswerType
from ai_service.offline_pipeline.parsing.markers import InterviewerTechniqueMarkers, InterviewerActionMarkers, InterviewerEmotionMarkers, InterviewerQuestionOpennessMarkers, GuestAnswerTypeMarkers

logger = logging.getLogger(__name__)


def normalize_text(text: str) -> str:
    text = text.lower().strip()
    text = text.replace("ё", "е")
    text = re.sub(r"\s+", " ", text)
    return text


def word_count(text: str) -> int:
    words = text.split()
    num_words = len(words)
    return num_words


def tokenize(text: str) -> list[str]:
    return re.findall(r"[а-яёa-z0-9-]+", normalize_text(text))


def contains_marker(text: str, marker: str) -> bool:
    text_norm = normalize_text(text)
    marker_norm = normalize_text(marker)

    if " " not in marker_norm:
        return marker_norm in tokenize(text_norm)

    pattern = rf"(?<!\w){re.escape(marker_norm)}(?!\w)"
    return re.search(pattern, text_norm) is not None


def contains_any_marker(text: str, markers) -> bool:
    return any(contains_marker(text, marker) for marker in markers)


def count_matching_markers(text: str, markers) -> int:
    return sum(1 for marker in markers if contains_marker(text, marker))


def starts_with_any(text: str, markers) -> bool:
    text_norm = normalize_text(text)
    markers_norm = [normalize_text(m) for m in markers]
    return any(text_norm.startswith(marker) for marker in markers_norm)


def ends_with_any(text: str, markers) -> bool:
    text_norm = normalize_text(text)
    markers_norm = [normalize_text(m) for m in markers]
    return any(text_norm.endswith(marker) for marker in markers_norm)


def add_score(scores: dict[str, int], label: str, points: int) -> None:
    scores[label] = scores.get(label, 0) + points


def choose_best(scores: dict[str, int], threshold: int = 1) -> str | None:
    if not scores:
        return None

    best_label, best_score = max(scores.items(), key=lambda x: x[1])
    if best_score < threshold:
        return None
    return best_label


class RuleAnnotator:
    def annotate_action(self, text: str) -> Action:
        markers = InterviewerActionMarkers
        lower_text = normalize_text(text)
        scores: dict[str, int] = {}
        word_number = word_count(lower_text)
        is_question = "?" in lower_text

        if contains_any_marker(lower_text, markers.BACKCHANNEL) and word_count(lower_text) <= 2:
            add_score(scores, Action.BACKCHANNEL, 2)
        if word_number <= 2:
            add_score(scores, Action.BACKCHANNEL, 1)
        if is_question:
            scores[Action.BACKCHANNEL] = 0

        matched_ack = count_matching_markers(text, markers.ACKNOWLEDGMENT)
        if matched_ack:
            add_score(scores, Action.ACKNOWLEDGMENT, 2*matched_ack)
        if word_number <= 5:
            add_score(scores, Action.ACKNOWLEDGMENT, 1)
        if is_question:
            scores[Action.ACKNOWLEDGMENT] = 0

        matched_clarification = count_matching_markers(text, markers.CLARIFICATION)
        if matched_clarification:
            add_score(scores, Action.CLARIFICATION, 2 * matched_clarification)
        if is_question:
            add_score(scores, Action.CLARIFICATION, 1)

        matched_topic_return = count_matching_markers(text, markers.TOPIC_RETURN)
        if matched_topic_return:
            add_score(scores, Action.TOPIC_RETURN, 2 * matched_topic_return)

        matched_transition = count_matching_markers(text, markers.TRANSITION_MARKERS)
        if matched_transition:
            add_score(scores, Action.TRANSITION, 2 * matched_transition)

        matched_summary = count_matching_markers(text, markers.SUMMARY)
        if matched_summary:
            add_score(scores, Action.SUMMARY, 2 * matched_summary)
        if word_number >= 6:
            add_score(scores, Action.SUMMARY, 1)

        if is_question:
            add_score(scores, Action.QUESTION, 2)

        action = choose_best(scores, threshold=1) or Action.UNCERTAIN
        logger.info("ACTION: %s - %s", action, lower_text)
        return action


    def annotate_question_openness(self, text: str) -> QuestionOpenness:
        markers = InterviewerQuestionOpennessMarkers
        lower_text = normalize_text(text)
        is_question = "?" in lower_text

        if not is_question:
            return QuestionOpenness.NOT_A_QUESTION

        if contains_any_marker(lower_text, markers.OPEN_QUESTION):
            #logger.info("OPEN_QUESTION: %s", lower_text)
            return QuestionOpenness.OPEN_QUESTION

        if (lower_text.startswith(tuple(m.lower() for m in markers.CLOSED_START)) or
                lower_text.endswith(tuple(m.lower() for m in markers.CLOSED_END))):
            #logger.info("CLOSED_QUESTION: %s", lower_text)
            return QuestionOpenness.CLOSED_QUESTION

        return QuestionOpenness.UNCERTAIN_QUESTION


    def annotate_emotion(self, text: str) -> Emotion:
        markers = InterviewerEmotionMarkers
        lower_text = normalize_text(text)
        is_question = "?" in lower_text

        if contains_any_marker(lower_text, markers.CHALLENGE_MARKERS):
            #logger.info("CHALLENGE_MARKERS: %s", lower_text)
            return Emotion.CHALLENGE

        elif contains_any_marker(lower_text, markers.EMPATHY_MARKERS):
            #logger.info("EMPATHY: %s", lower_text)
            return Emotion.EMPATHY

        elif not is_question:
            if ((word_count(lower_text) > 0 and contains_any_marker(lower_text, markers.COMMENTARY_MARKERS))
                    or word_count(lower_text) > 2):
                #logger.info("COMMENTARY: %s", lower_text)
                return Emotion.COMMENTARY

        return Emotion.NO_EMOTION


    def annotate_techniques(self, text: str) -> Technique:
        lower_text = text.lower().strip()
        markers = InterviewerTechniqueMarkers()

        if contains_any_marker(lower_text, markers.HYPOTHETICAL_MARKERS):
            return Technique.HYPOTHETICAL

        elif contains_any_marker(lower_text, markers.BEHAVIOUR):
            return Technique.BEHAVIORAL

        elif contains_any_marker(lower_text, markers.WHY_QUESTION):
            return Technique.WHY_QUESTION

        elif contains_any_marker(lower_text, markers.HOW_QUESTION):
            return Technique.HOW_QUESTION

        elif contains_any_marker(lower_text, markers.VALUES):
            return Technique.VALUES_EXPLORATION

        elif contains_any_marker(lower_text, markers.FACT_CHECK):
            return Technique.FACT_CHECK

        elif re.search(r"\bэто .+\?$", lower_text) or re.search(r"\bвы .+\?$", lower_text):
            if any(x in lower_text for x in ["смотрели", "говорили", "правда", "действительно"]):
                return Technique.FACT_CHECK

        elif contains_any_marker(lower_text, markers.REACTION):
            return Technique.REACTION

        elif contains_any_marker(lower_text, markers.QUANTITY):
            return Technique.QUANTITY

        elif contains_any_marker(lower_text, markers.DEFINITION):
            return Technique.DEFINITION

        elif contains_any_marker(lower_text, markers.RELATIONSHIP):
            return Technique.RELATIONSHIP

        elif contains_any_marker(lower_text, markers.TIME):
            return Technique.TIME

        elif contains_any_marker(lower_text, markers.BACKGROUND):
            return Technique.BACKGROUND

        elif contains_any_marker(lower_text, markers.OPINION):
            return Technique.OPINION

        elif contains_any_marker(lower_text, markers.CONFIRMATION):
            return Technique.CONFIRMATION

        elif contains_any_marker(lower_text, markers.EXAMPLE):
            return Technique.EXAMPLE

        return Technique.GENERAL



    def annotate_answer_type(self, text: str) -> AnswerType:
        lower_text = text.lower().strip()
        markers = GuestAnswerTypeMarkers()

        if word_count(lower_text) <= 8 and not contains_any_marker(lower_text, markers.STORY_MARKERS):
            return AnswerType.BRIEF

        if word_count(lower_text) >= 40 and contains_any_marker(lower_text, markers.STORY_MARKERS):
            return AnswerType.STRONG_WITH_EXAMPLE

        if 8 < word_count(lower_text) < 35 and contains_any_marker(lower_text, markers.VAGUE):
            if not  any(marker in lower_text for marker in markers.STORY_MARKERS):
                return AnswerType.VAGUE

        if word_count(lower_text) >= 25:
            return AnswerType.DETAILED_NO_EXAMPLE

        return AnswerType.UNCERTAIN
