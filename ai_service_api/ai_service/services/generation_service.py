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


class GenerateQuestionService:
    def __init__(self,
                 llm_client: BaseLLMClient,
                 profile_repository,
                 action_selector: ActionSelector,
                 template_selector: TemplateSelector,
                 max_number_question: int,
                 rag_service: OnlineRagSearchService) -> None:
        self.__llm_client = llm_client
        #self.__prompt_builder = BuildPromptService()
        self.__user_prompt_builder = BuildUserPromptService()
        self.__system_prompt_builder = BuildSystemPromptService()
        self.__profile_repository = profile_repository
        self.__action_selector = action_selector
        self.__template_selector = template_selector
        self.__max_number_question = max_number_question
        self.__rag_service = rag_service


    async def generate_question(self, input_data: GenerationRequest) -> GenerationResponse:
        current_answer = input_data.last_answer

        profile: InterviewerProfile = self.__profile_repository.get_profile(input_data.character_id)

        annotator = RuleAnnotator()
        answer_type = annotator.annotate_answer_type(current_answer)
        interview_position = self.extract_interview_position(input_data)
        previous_template_id = self.extract_previous_template(input_data)
        consecutive_followups = self.extract_consecutive_followups(input_data)

        selected_action = self.__action_selector.select(answer_type, interview_position, consecutive_followups)
        selected_template = self.__template_selector.select_template(selected_action.action, interview_position, previous_template_id)

        last_question = self.extract_last_question(input_data.full_interview_history)
        rag_examples = self.__rag_service.search(last_question, input_data.last_answer, 2)

        #built_prompt = self.__prompt_builder.build_prompt(input_data, profile, selected_template.template, rag_examples)
        system_prompt = self.__system_prompt_builder.build_prompt(profile, selected_template.template, input_data.character_id)
        user_prompt = self.__user_prompt_builder.build_prompt(input_data, selected_template.template, rag_examples)
        #generated_question = await self.__llm_client.generate_question(prompt=built_prompt.prompt)
        generated_question = await self.__llm_client.generate_question(system_prompt=system_prompt.prompt, user_prompt= user_prompt.prompt)

        updates_consecutive_followups = self.update_consecutive_followups(
            previous_count=input_data.consecutive_followups,
            selected_action=selected_action.action
        )
        used_template_id = getattr(selected_template.template, "structure")

        output_response = GenerationResponse(
            question=generated_question,
            used_profile=input_data.character_id,
            used_template_id=used_template_id,
            consecutive_followups=updates_consecutive_followups)
        return  output_response


    def extract_interview_position(self, input_data: GenerationRequest) -> float:
        if self.__max_number_question <= 0:
            return 0.0
        return min(input_data.phrase_id / self.__max_number_question, 1.0)

    @staticmethod
    def extract_consecutive_followups(input_data: GenerationRequest) -> int:
        return input_data.consecutive_followups

    @staticmethod
    def extract_previous_template(input_data: GenerationRequest) -> str | None:
        return input_data.previous_template_id

    def update_consecutive_followups(self, previous_count: int, selected_action: str) -> int:
        #if selected_action not in {Action.TRANSITION, DialogueAct.OPEN_QUESTION, DialogueAct.CLOSED_QUESTION}:
        if selected_action in {Action.TRANSITION, Action.BACK_CHANNEL, Action.ACKNOWLEDGMENT}:
            return 0
        return previous_count + 1

    @staticmethod
    def extract_last_question(history: list[InterviewPart]) -> str | None:
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