import re

from categories import DialogueAct, Technique, AnswerType
from markers import InterviewerTechniqueMarkers, InterviewerDialogueActMarkers, GuestAnswerTypeMarkers


def word_count(text: str) -> int:
    words = text.split()
    num_words = len(words)
    return num_words


class RuleAnnotator:

    def annotate_dialogue_act(self, text: str) -> DialogueAct:
        markers = InterviewerDialogueActMarkers()
        lower_text = text.lower().strip()

        if any(marker in lower_text for marker in markers.BACKCHANNEL):
            return DialogueAct.BACKCHANNEL

        elif any(marker in lower_text for marker in markers.ACKNOWLEDGMENT):
            return DialogueAct.ACKNOWLEDGMENT

        elif any(marker in lower_text for marker in markers.TRANSITION_MARKERS):
            return DialogueAct.TRANSITION

        elif any(marker in lower_text for marker in markers.CLARIFICATION):
            return DialogueAct.CLARIFICATION

        elif any(marker in lower_text for marker in markers.CHALLENGE_MARKERS):
            return DialogueAct.CHALLENGE

        elif "?" in lower_text and any(marker in lower_text for marker in markers.OPEN_QUESTION):
            return DialogueAct.OPEN_QUESTION

        elif "?" in lower_text and (text.endswith(markers.CLOSED_END) or text.startswith(markers.CLOSED_START)):
            return DialogueAct.CLOSED_QUESTION

        elif any(marker in lower_text for marker in markers.EMPATHY_MARKERS):
            return DialogueAct.EMPATHY

        elif any(marker in lower_text for marker in markers.TOPIC_RETURN):
            return DialogueAct.TOPIC_RETURN

        elif any(marker in lower_text for marker in markers.SUMMARY):
            return DialogueAct.SUMMARY

        elif "?" not in lower_text:
            if ((word_count(lower_text) > 0 and any(marker in lower_text for marker in markers.COMMENTARY_MARKERS))
                    or word_count(lower_text) > 2):
                return DialogueAct.COMMENTARY

        return DialogueAct.UNCERTAIN


    def annotate_techniques(self, text: str) -> Technique:
        lower_text = text.lower().strip()
        markers = InterviewerTechniqueMarkers()

        if "?" not in lower_text:
            return Technique.NOT_A_QUESTION

        elif any(marker in lower_text for marker in markers.HYPOTHETICAL_MARKERS):
            return Technique.HYPOTHETICAL

        elif any(marker in lower_text for marker in markers.BEHAVIOUR):
            return Technique.BEHAVIORAL

        elif any(marker in lower_text for marker in markers.WHY_QUESTION):
            return Technique.WHY_QUESTION

        elif any(marker in lower_text for marker in markers.HOW_QUESTION):
            return Technique.HOW_QUESTION

        elif any(marker in lower_text for marker in markers.VALUES):
            return Technique.VALUES_EXPLORATION

        elif any(marker in lower_text for marker in markers.FACT_CHECK):
            return Technique.FACT_CHECK

        elif re.search(r"\bэто .+\?$", lower_text) or re.search(r"\bвы .+\?$", lower_text):
            if any(x in lower_text for x in ["смотрели", "говорили", "правда", "действительно"]):
                return Technique.FACT_CHECK

        elif any(marker in lower_text for marker in markers.REACTION):
            return Technique.REACTION

        elif any(marker in lower_text for marker in markers.QUANTITY):
            return Technique.QUANTITY

        elif any(marker in lower_text for marker in markers.DEFINITION):
            return Technique.DEFINITION

        elif any(marker in lower_text for marker in markers.RELATIONSHIP):
            return Technique.RELATIONSHIP

        elif any(marker in lower_text for marker in markers.TIME):
            return Technique.TIME

        elif any(marker in lower_text for marker in markers.BACKGROUND):
            return Technique.BACKGROUND

        elif any(marker in lower_text for marker in markers.OPINION):
            return Technique.OPINION

        elif any(marker in lower_text for marker in markers.CONFIRMATION):
            return Technique.CONFIRMATION

        elif any(marker in lower_text for marker in markers.EXAMPLE):
            return Technique.EXAMPLE

        return Technique.GENERAL



    def annotate_answer_type(self, text: str) -> AnswerType:
        lower_text = text.lower().strip()
        markers = GuestAnswerTypeMarkers()

        if word_count(lower_text) <= 8 and not any(marker in lower_text for marker in markers.STORY_MARKERS):
            return AnswerType.BRIEF

        if word_count(lower_text) >= 40 and any(marker in lower_text for marker in markers.STORY_MARKERS):
            return AnswerType.STRONG_WITH_EXAMPLE

        if 8 < word_count(lower_text) < 35 and any(marker in lower_text for marker in markers.VAGUE):
            if not  any(marker in lower_text for marker in markers.STORY_MARKERS):
                return AnswerType.VAGUE

        if word_count(lower_text) >= 25:
            return AnswerType.DETAILED_NO_EXAMPLE

        return AnswerType.UNCERTAIN
