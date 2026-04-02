from ai_service.models.generation import GenerationRequest, GenerationResponse
from ai_service.services.llm_service import BaseLLMClient
from ai_service.services.build_prompt_service import BuildPromptService
from ai_service.exeptions.generation_error import CharacterNotFound
from ai_service_api.ai_service.models.build_profile import InterviewerProfile
from ai_service_api.ai_service.selection.action_selector import ActionSelector
from ai_service_api.ai_service.selection.template_selector import TemplateSelector
from ai_service_api.ai_service.offline_pipeline.parsing.rule_anotator import RuleAnnotator

class GenerateQuestionService:
    def __init__(self,
                 llm_client: BaseLLMClient,
                 interview_characters: set[str],
                 profile_repository,
                 action_selector: ActionSelector,
                 template_selector: TemplateSelector) -> None:
        self.__llm_client = llm_client
        self.__interview_characters = interview_characters
        self.__prompt_builder = BuildPromptService()
        self.__profile_repository = profile_repository
        self.__action_selector = action_selector
        self.__template_selector = template_selector


    async def generate_question(self, input_data: GenerationRequest) -> GenerationResponse:
        current_answer = input_data.last_answer

        if input_data.character_id not in self.__interview_characters:
            raise CharacterNotFound(input_data.character_id)

        profile: InterviewerProfile = self.__profile_repository.get_profile(input_data.character_id)

        annotator = RuleAnnotator()
        answer_type = annotator.annotate_answer_type(current_answer)
        interview_position = self.__extract_interview_position()
        previous_template_id = self.__extract_previous_template()
        consecutive_followups = self.__extract_consecutive_followups()

        selected_action = self.__action_selector.select(answer_type, interview_position, consecutive_followups)
        selected_template = self.__template_selector.select_template(selected_action.action, interview_position, previous_template_id)

        built_prompt = self.__prompt_builder.build_prompt(input_data, profile, selected_template.template)

        generated_question = await self.__llm_client.generate_question(built_prompt.prompt)

        output_response = GenerationResponse(question=generated_question, used_profile=input_data.character_id)

        return  output_response

    @staticmethod
    def __extract_interview_position() -> float:
        return 0.0 # будет добавлена логика

    @staticmethod
    def __extract_consecutive_followups() -> int:
        return 0  # будет добавлена логика

    @staticmethod
    def __extract_previous_template() -> str:
        return " "  # будет добавлена логика