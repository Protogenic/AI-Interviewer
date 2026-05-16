import re
import logging
from typing import List

from ai_service.offline_pipeline.categories import Action, QuestionOpenness, Emotion, Technique, AnswerType
from ai_service.offline_pipeline.parsing.markers import InterviewerTechniqueMarkers, InterviewerActionMarkers, InterviewerEmotionMarkers, InterviewerQuestionOpennessMarkers, GuestAnswerTypeMarkers
logger = logging.getLogger(__name__)


def normalize_text(text: str) -> str:
    text = text.lower().strip()
    text = text.replace("ё", "е")
    text = re.sub(r'[\u200b\u200c\u200d\ufeff]', '', text)
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
            add_score(scores, Action.BACK_CHANNEL, 2)
        if word_number <= 2:
            add_score(scores, Action.BACK_CHANNEL, 1)
        if is_question:
            scores[Action.BACK_CHANNEL] = 0

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
        #logger.info("ACTION: %s - %s", action, lower_text)
        return action


    def annotate_question_openness(self, text: str) -> QuestionOpenness:
        markers = InterviewerQuestionOpennessMarkers
        lower_text = normalize_text(text)
        is_question = "?" in lower_text
        scores: dict[str, int] = {}
        word_number = word_count(lower_text)

        if not is_question:
            #logger.info("QUESTION: %s - %s", QuestionOpenness.NOT_A_QUESTION, lower_text)
            return QuestionOpenness.NOT_A_QUESTION

        if starts_with_any(lower_text, tuple(m.lower() for m in markers.CLOSED_START)):
            return QuestionOpenness.CLOSED_QUESTION

        if ends_with_any(lower_text, tuple(m.lower() for m in markers.CLOSED_END)):
            return QuestionOpenness.CLOSED_QUESTION

        matched_open = count_matching_markers(text, markers.OPEN_QUESTION)
        if matched_open:
            add_score(scores, QuestionOpenness.OPEN_QUESTION, 2 * matched_open)

        matched_blitz = count_matching_markers(text, markers.BLITZ)
        if matched_blitz:
            add_score(scores, QuestionOpenness.BLITZ, 2 * matched_blitz)

        if word_number < 6:
            add_score(scores, QuestionOpenness.CLOSED_QUESTION, 1)

        question = choose_best(scores, threshold=1) or QuestionOpenness.UNCERTAIN_QUESTION
        #if question == QuestionOpenness.UNCERTAIN_QUESTION:
            #print(repr(text))
            #print(repr(normalize_text(text)))
            #logger.info("QUESTION: %s - %s", question, lower_text)

        return question


    def annotate_emotion(self, text: str) -> Emotion:
        markers = InterviewerEmotionMarkers
        lower_text = normalize_text(text)
        is_question = "?" in lower_text

        if contains_any_marker(lower_text, markers.CHALLENGE_MARKERS):
            # logger.info("CHALLENGE_MARKERS: %s", lower_text)
            return Emotion.CHALLENGE

        elif contains_any_marker(lower_text, markers.EMPATHY_MARKERS):
            #logger.info("EMPATHY: %s", lower_text)
            return Emotion.EMPATHY

        elif not is_question:
            if ((word_count(lower_text) > 0 and contains_any_marker(lower_text, markers.COMMENTARY_MARKERS))
                    or word_count(lower_text) > 2):
                #logger.info("COMMENTARY: %s", lower_text)
                return Emotion.COMMENTARY

        #logger.info("NO_EMOTION: %s", lower_text)
        return Emotion.NO_EMOTION


    def annotate_techniques(self, text: str) -> List[Technique]:
        lower_text = normalize_text(text)
        markers = InterviewerTechniqueMarkers()
        techniques: List[Technique] = []

        if contains_any_marker(lower_text, markers.HYPOTHETICAL_MARKERS):
            techniques.append(Technique.HYPOTHETICAL)

        if contains_any_marker(lower_text, markers.BEHAVIOUR):
            techniques.append(Technique.BEHAVIORAL)

        if contains_any_marker(lower_text, markers.WHY_QUESTION):
            techniques.append(Technique.WHY_QUESTION)

        if contains_any_marker(lower_text, markers.HOW_QUESTION):
            techniques.append(Technique.HOW_QUESTION)

        if contains_any_marker(lower_text, markers.VALUES):
            techniques.append(Technique.VALUES_EXPLORATION)

        if contains_any_marker(lower_text, markers.FACT_CHECK):
            techniques.append(Technique.FACT_CHECK)

        if re.search(r"\bэто .+\?$", lower_text) or re.search(r"\bвы .+\?$", lower_text):
            if any(x in lower_text for x in ["смотрели", "говорили", "правда", "действительно"]):
                if Technique.FACT_CHECK not in techniques:
                    techniques.append(Technique.FACT_CHECK)

        if contains_any_marker(lower_text, markers.REACTION):
            techniques.append(Technique.REACTION)

        if contains_any_marker(lower_text, markers.QUANTITY):
            techniques.append(Technique.QUANTITY)

        if contains_any_marker(lower_text, markers.DEFINITION):
            techniques.append(Technique.DEFINITION)

        if contains_any_marker(lower_text, markers.RELATIONSHIP):
            techniques.append(Technique.RELATIONSHIP)

        if contains_any_marker(lower_text, markers.TIME):
            techniques.append(Technique.TIME)

        if contains_any_marker(lower_text, markers.BACKGROUND):
            techniques.append(Technique.BACKGROUND)

        if contains_any_marker(lower_text, markers.OPINION):
            techniques.append(Technique.OPINION)

        if contains_any_marker(lower_text, markers.CONFIRMATION):
            techniques.append(Technique.CONFIRMATION)

        if contains_any_marker(lower_text, markers.EXAMPLE):
            techniques.append(Technique.EXAMPLE)

        if techniques:
            return techniques

        return [Technique.GENERAL]



    def annotate_answer_type(self, text: str) -> AnswerType:
        lower_text = normalize_text(text)
        markers = GuestAnswerTypeMarkers()
        word_c = word_count(lower_text)

        if text == "":
            return AnswerType.NOT_ANSWER

        if contains_any_marker(lower_text, markers.REFUSAL):
            return AnswerType.REFUSAL

        if word_c < 5 and contains_any_marker(lower_text, markers.AGREEMENT):
            return AnswerType.BACK_CHANNEL

        if contains_any_marker(lower_text, markers.AGREEMENT):
            return AnswerType.AGREEMENT

        if "?" in lower_text and word_c <= 12:
            return AnswerType.COUNTER_QUESTION

        has_story_markers = contains_any_marker(lower_text, markers.STORY)
        has_direct_speech = ('"' in lower_text) or ("«" in lower_text) or ("»" in lower_text) or (":" in lower_text and word_c > 10)

        has_time_fact = bool(re.search(r"\b\d+\s*(год|года|лет)\s*назад\b", lower_text)) or \
                            bool(re.search(r"\b(в прошлом году|позавчера|вчера|зимой|летом|осенью|весной)\b", lower_text))

        if word_c >= 20 and (has_story_markers or has_direct_speech or has_time_fact):
            return AnswerType.STORY_WITH_EXAMPLE

        filler_hits = sum(1 for x in markers.VAGUE if x in lower_text)
        correction_hits = sum(1 for x in markers.SELF_CORRECTION if x in lower_text)
        filler_density = filler_hits / max(word_c, 1)

        if word_c >= 5 and (filler_density >= 0.03):
            return AnswerType.VAGUE

        if word_c >= 5 and (filler_density >= 0.08 or correction_hits >= 1):
            return AnswerType.STRONG_VAGUE

        has_reasoning = contains_any_marker(lower_text, markers.REASONING)
        if word_c >= 20 and has_reasoning:
            return AnswerType.EXPLANATION

        if word_c <= 15 and contains_any_marker(lower_text, markers.OPINION):
            return AnswerType.SHORT_OPINION

        if word_c <= 12 and (has_time_fact or re.search(r"\b(в|на)\s+[а-яa-z\-]+\b", lower_text) or re.search(r"\b\d+\b", lower_text)):
            return AnswerType.SHORT_FACT

        return AnswerType.UNCERTAIN
