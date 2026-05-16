import sys
import types
import json
import pytest
from unittest.mock import MagicMock


def _make_stub(name: str) -> types.ModuleType:
    mod = types.ModuleType(name)
    mod.__spec__ = None
    return mod


for _mod_name in [
    "chromadb",
    "sentence_transformers",
    "huggingface_hub",
]:
    if _mod_name not in sys.modules:
        sys.modules[_mod_name] = _make_stub(_mod_name)

_chroma = sys.modules["chromadb"]
_chroma.PersistentClient = MagicMock

_st = sys.modules["sentence_transformers"]
_st.SentenceTransformer = MagicMock

from ai_service.models.build_profile import (
    InterviewerProfile,
    LinguisticProfile,
    Template,
)
from ai_service.models.generation import GenerationRequest, InterviewPart
from ai_service.models.rag import RagExample
from ai_service.offline_pipeline.categories import Action, Technique


@pytest.fixture
def linguistic_profile():
    return LinguisticProfile(
        empathy_density=0.1,
        hedging_density=0.05,
        pressure_density=0.02,
        filler_density=0.03,
        formal_density=0.01,
        provocation_density=0.01,
        avg_question_length=15.0,
        avg_phrase_length=12.0,
        multi_sentence_ratio=0.4,
        number_of_questions=50.0,
    )


@pytest.fixture
def make_template():
    def _make(
        structure="question",
        frequency=10,
        action=Action.QUESTION.value,
        question_openness="open_question",
        emotion="neutral",
        techniques=None,
        avg_position=0.5,
        reactivity=None,
        examples=None,
        template_id=None,
    ):
        t = Template(
            structure=structure,
            frequency=frequency,
            action=action,
            question_openness=question_openness,
            emotion=emotion,
            techniques=techniques or [Technique.WHY_QUESTION],
            avg_position=avg_position,
            reactivity=reactivity or [],
            examples=examples or ["Пример вопроса?"],
        )
        if template_id is not None:
            object.__setattr__(t, "template_id", template_id)
        return t

    return _make


@pytest.fixture
def interviewer_profile(linguistic_profile, make_template):
    templates = [
        make_template(
            structure="question",
            action=Action.QUESTION.value,
            techniques=[Technique.WHY_QUESTION],
            avg_position=0.3,
            frequency=10,
        ),
        make_template(
            structure="bridge+question",
            action=Action.TRANSITION.value,
            techniques=[Technique.FACT_CHECK],
            avg_position=0.7,
            frequency=5,
        ),
        make_template(
            structure="acknowledgment",
            action=Action.ACKNOWLEDGMENT.value,
            techniques=[Technique.CONFIRMATION],
            avg_position=0.5,
            frequency=8,
        ),
    ]
    return InterviewerProfile(
        interviewer_id="dud",
        linguistic_profile=linguistic_profile,
        reactivity_matrix={
            "explanation": {"question": 5, "transition": 2},
            "short_fact": {"clarification": 3, "question": 2},
            "agreement": {"question": 4, "back_channel": 1},
        },
        templates=templates,
        characteristic_phrases=["Подождите", "То есть как?", "Серьёзно?"],
    )


@pytest.fixture
def simple_generation_request():
    return GenerationRequest(
        session_id="sess-001",
        character_id="dud",
        user_name="Иван",
        user_info="Предприниматель, 35 лет",
        last_answer="Я работаю уже пять лет и очень доволен результатами.",
        full_interview_history=[
            InterviewPart(role="interviewer", text="Расскажите о себе."),
            InterviewPart(role="guest", text="Я работаю уже пять лет и очень доволен результатами."),
        ],
        max_number_questions=20,
        phrase_id=5,
        previous_template_id=None,
        consecutive_followups=0,
    )


@pytest.fixture
def rag_examples():
    return [
        RagExample(
            score=0.85,
            interview_id="int-001",
            source_file="dud_001.jsonl",
            question_replica_id=3,
            question_text="Как вы к этому пришли?",
            answer_text="Это долгая история.",
        ),
        RagExample(
            score=0.72,
            interview_id="int-002",
            source_file="dud_002.jsonl",
            question_replica_id=7,
            question_text="Что вас мотивирует?",
            answer_text="Желание помогать людям.",
        ),
    ]


@pytest.fixture
def profile_json_data():
    return {
        "interviewer_id": "dud",
        "linguistic_profile": {
            "empathy_density": 0.1,
            "hedging_density": 0.05,
            "pressure_density": 0.02,
            "filler_density": 0.03,
            "formal_density": 0.01,
            "provocation_density": 0.01,
            "avg_question_length": 15.0,
            "avg_phrase_length": 12.0,
            "multi_sentence_ratio": 0.4,
            "number_of_questions": 50.0,
        },
        "reactivity_matrix": {
            "explanation": {"question": 5, "transition": 2},
            "short_fact": {"clarification": 3, "question": 2},
        },
        "templates": [
            {
                "structure": "question",
                "frequency": 10,
                "action": "question",
                "question_openness": "open_question",
                "emotion": "neutral",
                "techniques": ["why_question"],
                "avg_position": 0.3,
                "reactivity": [],
                "examples": ["Как так получилось?"],
            }
        ],
        "characteristic_phrases": ["Подождите", "То есть как?"],
    }


@pytest.fixture
def profile_json_file(profile_json_data, tmp_path):
    profile_dir = tmp_path / "profiles"
    profile_dir.mkdir()
    profile_path = profile_dir / "dud_profile.json"
    profile_path.write_text(json.dumps(profile_json_data), encoding="utf-8")
    return profile_dir


@pytest.fixture
def reactivity_matrix():
    return {
        "explanation": {"question": 5, "transition": 2, "clarification": 1},
        "short_fact": {"clarification": 3, "question": 2},
        "agreement": {"question": 4, "back_channel": 1, "acknowledgment": 2},
        "refusal": {"transition": 5},
        "story_with_example": {"question": 3, "summary": 2},
    }
