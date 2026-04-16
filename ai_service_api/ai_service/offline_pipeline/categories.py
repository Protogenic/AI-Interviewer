from enum import Enum


class Action(str, Enum):
    BACK_CHANNEL = "back_channel" #"дать сигнал обратной связи"
    ACKNOWLEDGMENT = "acknowledgment" #"выразить согласие или понимание"
    CLARIFICATION = "clarification" #"уточнить детали или спросить что-то по той же теме"
    TRANSITION = "transition" #"перейти к новой теме или вернуться к какой-то"
    SUMMARY = "summary" #"подытожить или перефразировать для подтверждения"
    QUESTION = "question" #"задать вопрос"
    UNCERTAIN = "uncertain" #неопределено


class QuestionOpenness(str, Enum):
    OPEN_QUESTION = "open_question"
    CLOSED_QUESTION = "closed_question"
    NOT_A_QUESTION = "not_a_question"
    BLITZ = "blitz"
    UNCERTAIN_QUESTION = "uncertain_question"


class Emotion(str, Enum):
    NEUTRAL = "neutral"
    CHALLENGE = "challenge"
    EMPATHY = "empathy"
    COMMENTARY = "commentary"
    NO_EMOTION = "no_emotion"


class AnswerType(str, Enum):
    BACK_CHANNEL = "back_channel"
    AGREEMENT = "agreement"
    REFUSAL = "refusal"
    DONT_KNOW = "dont_know"
    COUNTER_QUESTION = "counter_question"
    SHORT_FACT = "short_fact"
    SHORT_OPINION = "short_opinion"
    EXPLANATION = "explanation"
    STORY_WITH_EXAMPLE = "story_with_example"
    VAGUE = "vague"
    STRONG_VAGUE = "strong_vague"
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