from enum import Enum


class DialogueAct(str, Enum):
    BACKCHANNEL = "backchannel"
    ACKNOWLEDGMENT = "acknowledgment"
    CLARIFICATION = "clarification"
    OPEN_QUESTION = "open_question"
    CLOSED_QUESTION = "closed_question"
    TRANSITION = "transition"
    CHALLENGE = "challenge"
    EMPATHY = "empathy"
    TOPIC_RETURN = "topic_return"
    COMMENTARY = "commentary"
    SUMMARY = "summary"
    UNCERTAIN = "uncertain"


class AnswerType(str, Enum):
    STRONG_WITH_EXAMPLE = "strong_with_example"
    DETAILED_NO_EXAMPLE = "detailed_no_example"
    VAGUE = "vague"
    BRIEF = "brief"
    UNCERTAIN = "uncertain"


class Technique(str, Enum):
    BEHAVIORAL = "behavioral"
    WHY_QUESTION = "why_question"
    HOW_QUESTION = "how_question"
    VALUES_EXPLORATION = "values_exploration"
    FACT_CHECK = "fact_checking"
    DEFINITION = "definition_request"
    REACTION = "reaction_request"
    QUANTITY = "quantity_request"
    TIME = "time_request"
    BACKGROUND = "background_request"
    RELATIONSHIP = "relationship"
    OPINION = "opinion_request"
    EXAMPLE = "example_request"
    HYPOTHETICAL = "hypothetical"
    CONFIRMATION = "confirmation"
    FOLLOWUP = "follow_up"
    GENERAL = "general"
    NOT_A_QUESTION = "not_a_question"


class ComponentType(str, Enum):
    ACKNOWLEDGMENT = "acknowledgment"
    BRIDGE = "bridge"
    PARAPHRASE = "paraphrase"
    EMPATHY = "empathy"
    PREAMBLE = "preamble"
    QUESTION = "question"
    REQUEST = "request"