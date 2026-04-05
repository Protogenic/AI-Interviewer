from enum import Enum


class Action(str, Enum):
    BACKCHANNEL = "backchannel"
    ACKNOWLEDGMENT = "acknowledgment"
    CLARIFICATION = "clarification"
    TRANSITION = "transition"
    TOPIC_RETURN = "topic_return"
    SUMMARY = "summary"
    QUESTION = "question"
    UNCERTAIN = "uncertain"


class QuestionOpenness(str, Enum):
    OPEN_QUESTION = "open_question"
    CLOSED_QUESTION = "closed_question"
    NOT_A_QUESTION = "not_a_question"
    UNCERTAIN_QUESTION = "uncertain_question"


class Emotion(str, Enum):
    NEUTRAL = "neutral"
    CHALLENGE = "challenge"
    EMPATHY = "empathy"
    COMMENTARY = "commentary"
    NO_EMOTION = "no_emotion"


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


class ComponentType(str, Enum):
    ACKNOWLEDGMENT = "acknowledgment"
    BRIDGE = "bridge"
    PARAPHRASE = "paraphrase"
    EMPATHY = "empathy"
    QUESTION = "question"
    REQUEST = "request"
    TEXT = "text"