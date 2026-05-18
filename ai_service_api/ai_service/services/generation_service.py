"""Сервис генерации вопроса: оркестрирует выбор действия, шаблона, RAG и вызов LLM."""

from ai_service.models.generation import GenerationRequest, GenerationResponse
from ai_service.services.llm_service import BaseLLMClient
from ai_service.services.build_prompt_service import BuildUserPromptService, BuildSystemPromptService
from ai_service.models.build_profile import InterviewerProfile
from ai_service.selection.action_selector import ActionSelector
from ai_service.selection.template_selector import TemplateSelector
from ai_service.offline_pipeline.parsing.rule_anotator import RuleAnnotator
from ai_service.offline_pipeline.categories import Action
from ai_service.services.rag_service import OnlineRagSearchService
from ai_service.models.generation import InterviewPart
from ai_service.services.prompt_guard import guard_generation_input


class GenerateQuestionService:
    """Генерирует очередной вопрос интервьюера по входным данным сессии."""

    def __init__(self,
                 llm_client: BaseLLMClient,
                 profile_repository,
                 action_selector: ActionSelector,
                 template_selector: TemplateSelector,
                 max_number_question: int,
                 rag_service: OnlineRagSearchService) -> None:
        self.__llm_client = llm_client
        self.__user_prompt_builder = BuildUserPromptService()
        self.__system_prompt_builder = BuildSystemPromptService()
        self.__profile_repository = profile_repository
        self.__action_selector = action_selector
        self.__template_selector = template_selector
        self.__max_number_question = max_number_question
        self.__rag_service = rag_service


    async def generate_question(self, input_data: GenerationRequest) -> GenerationResponse:
        """Полный цикл генерации: аннотация ответа, выбор действия и шаблона, RAG, запрос в LLM."""
        guarded = guard_generation_input(
            user_name=input_data.user_name,
            user_info=input_data.user_info,
            interview_topic=input_data.interview_topic,
            last_answer=input_data.last_answer,
            history_texts=[p.text for p in input_data.full_interview_history],
        )
        guarded_input = input_data.model_copy(update={
            "user_name": guarded.user_name,
            "user_info": guarded.user_info,
            "interview_topic": guarded.interview_topic,
            "last_answer": guarded.last_answer,
            "full_interview_history": [
                InterviewPart(role=part.role, text=text)
                for part, text in zip(input_data.full_interview_history, guarded.history_texts)
            ],
        })

        current_answer = guarded_input.last_answer

        profile: InterviewerProfile = self.__profile_repository.get_profile(guarded_input.character_id)

        annotator = RuleAnnotator()
        answer_type = annotator.annotate_answer_type(current_answer)
        interview_position = self.extract_interview_position(guarded_input)
        previous_template_id = self.extract_previous_template(guarded_input)
        consecutive_followups = self.extract_consecutive_followups(guarded_input)

        selected_action = self.__action_selector.select(answer_type, interview_position, consecutive_followups)
        selected_template = self.__template_selector.select_template(selected_action.action, interview_position, previous_template_id)

        last_question = self.extract_last_question(guarded_input.full_interview_history)
        rag_examples = self.__rag_service.search(last_question, guarded_input.last_answer, 2)

        system_prompt = self.__system_prompt_builder.build_prompt(profile, selected_template.template, guarded_input.character_id, guarded_input.interview_topic)
        user_prompt = self.__user_prompt_builder.build_prompt(guarded_input, selected_template.template, rag_examples)
        generated_question = await self.__llm_client.generate_question(
            system_prompt=system_prompt.prompt,
            user_prompt=user_prompt.prompt,
        )

        updated_consecutive_followups = self.update_consecutive_followups(
            previous_count=guarded_input.consecutive_followups,
            selected_action=selected_action.action,
        )

        return GenerationResponse(
            question=generated_question,
            used_profile=guarded_input.character_id,
            used_template_id=getattr(selected_template.template, "structure"),
            consecutive_followups=updated_consecutive_followups,
        )


    def extract_interview_position(self, input_data: GenerationRequest) -> float:
        """Возвращает позицию в интервью как долю от 0.0 до 1.0."""
        if self.__max_number_question <= 0:
            return 0.0
        return min(input_data.phrase_id / self.__max_number_question, 1.0)


    @staticmethod
    def extract_consecutive_followups(input_data: GenerationRequest) -> int:
        """Возвращает количество уточняющих вопросов подряд из запроса."""
        return input_data.consecutive_followups


    @staticmethod
    def extract_previous_template(input_data: GenerationRequest) -> str | None:
        """Возвращает идентификатор предыдущего шаблона для защиты от повтора."""
        return input_data.previous_template_id

    def update_consecutive_followups(self, previous_count: int, selected_action: str) -> int:
        """Сбрасывает счётчик уточнений при переходе к новой теме, иначе увеличивает на 1."""
        if selected_action in {Action.TRANSITION}:
            return 0
        return previous_count + 1


    @staticmethod
    def extract_last_question(history: list[InterviewPart]) -> str | None:
        """Извлекает текст последнего вопроса интервьюера перед текущим ответом гостя."""
        seen_guest = False
        for part in reversed(history):
            if not seen_guest and part.role == "guest":
                if (part.text or "").strip():
                    seen_guest = True
                continue

            if seen_guest and part.role == "interviewer":
                text = (part.text or "").strip()
                if text:
                    return text

        return None