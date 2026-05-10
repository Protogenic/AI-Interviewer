class GenerationError(Exception):
    pass


class CharacterNotFound(GenerationError):
    """Ошибка: запрошенный интервьюер не найден в базе"""
    def __init__(self, character_id: str):
        self.__character_id = character_id
        self.__message = f"Character '{character_id}' does not exist in the database."
        super().__init__(self.__message)


class UnknownInterviewerError(GenerationError):
    """Идентификатор интервьюера не найден в таблице инструкций или маркеров."""
    def __init__(self, character_id: str):
        self.__character_id = character_id
        self.__message = f"No instructions or markers registered for interviewer '{character_id}."
        super().__init__(self.__message)


class ProfileLoadError(GenerationError):
    """Профиль интервьюера не удалось загрузить или распарсить."""
    def __init__(self, character_id: str, reason: str) -> None:
        self.character_id = character_id
        self.reason = reason
        super().__init__(f"Failed to load profile for '{character_id}': {reason}")


class ProfileDataCorruptedError(ProfileLoadError):
    """JSON-профиль структурно повреждён или содержит недопустимые значения."""


class RagIndexNotFoundError(GenerationError):
    """Файлы RAG-индекса (манифест или persist-директория) отсутствуют на диске."""

    def __init__(self, character_id: str, missing_path: str) -> None:
        self.character_id = character_id
        self.missing_path = missing_path
        super().__init__(
            f"RAG index for '{character_id}' is missing: '{missing_path}'. "
            "Run the offline pipeline to build the index."
        )


class RagManifestCorruptedError(RagIndexNotFoundError):
    """Манифест RAG-индекса присутствует на диске, но повреждён или содержит некорректный JSON."""

    def __init__(self, character_id: str, manifest_path: str, reason: str) -> None:
        self.reason = reason
        super().__init__(character_id=character_id, missing_path=manifest_path)
        self.args = (
            f"RAG manifest for '{character_id}' at '{manifest_path}' is corrupted: {reason}. "
            "Run the offline pipeline to rebuild the index.",
        )


class RagStoreUnavailableError(RagIndexNotFoundError):
    """Векторное хранилище ChromaDB не удалось открыть для существующего persist-каталога."""

    def __init__(self, character_id: str, persist_dir: str, reason: str) -> None:
        self.reason = reason
        super().__init__(character_id=character_id, missing_path=persist_dir)
        self.args = (
            f"RAG vector store for '{character_id}' at '{persist_dir}' is unavailable: {reason}.",
        )


class EmbeddingModelError(GenerationError):
    """Модель эмбеддингов не загрузилась или не смогла закодировать текст."""

    def __init__(self, model_name: str, reason: str) -> None:
        self.model_name = model_name
        self.reason = reason
        super().__init__(f"Embedding model '{model_name}' failed: {reason}")


class TemplateSelectionError(GenerationError):
    """Не удалось выбрать шаблон для заданного действия и позиции интервью."""

    def __init__(self, action: str, interview_position: float) -> None:
        self.action = action
        self.interview_position = interview_position
        super().__init__(
            f"No templates available for action='{action}' "
            f"at interview_position={interview_position:.3f}."
        )


class LLMConfigurationError(GenerationError):
    """Провайдер LLM не поддерживается или не настроен в переменных окружения."""

    def __init__(self, provider: str) -> None:
        self.provider = provider
        super().__init__(
            f"Unsupported or misconfigured LLM provider: '{provider}'. "
            "Set LLM_PROVIDER to one of: openai, ollama, ollama_openai, "
            "deepseek, groq, gemini, mistral, openrouter, together."
        )


class LLMResponseError(GenerationError):
    """LLM вернул пустой или структурно некорректный ответ."""

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(f"LLM returned an invalid response: {reason}")


class RagSearchError(GenerationError):
    """Сбой при выполнении запроса к ChromaDB во время онлайн-поиска."""

    def __init__(self, character_id: str, reason: str) -> None:
        self.character_id = character_id
        self.reason = reason
        super().__init__(f"RAG search failed for '{character_id}': {reason}")


class PipelineError(Exception):
    """Base exception for the offline data-processing pipeline."""


class DataDirectoryNotFoundError(PipelineError):
    """Директория с исходными данными не найдена."""

    def __init__(self, path: str) -> None:
        self.path = path
        super().__init__(
            f"Data directory not found: '{path}'. "
            "Make sure the cleaned data has been placed at the expected location."
        )


class DuplicateChunkError(PipelineError):
    """В батче обнаружены дублирующиеся идентификаторы чанков."""

    def __init__(self, duplicate_ids: list[str]) -> None:
        self.duplicate_ids = duplicate_ids
        preview = duplicate_ids[:5]
        super().__init__(
            f"Duplicate chunk IDs detected before upsert "
            f"({len(duplicate_ids)} total). First few: {preview}"
        )


class IndexBuildError(PipelineError):
    """Общая ошибка построения RAG-индекса в ChromaDB."""

    def __init__(self, character_id: str, reason: str) -> None:
        self.character_id = character_id
        self.reason = reason
        super().__init__(f"Failed to build RAG index for '{character_id}': {reason}")


class IndexStorageError(PipelineError):
    """Ошибка записи данных в ChromaDB при построении оффлайн-индекса."""

    def __init__(self, character_id: str, reason: str) -> None:
        self.character_id = character_id
        self.reason = reason
        super().__init__(f"Failed to store index data for '{character_id}': {reason}")