from pydantic import BaseModel
from pathlib import Path


class RagChunk(BaseModel):
    interview_id: str
    source_file: str
    question_replica_id: int
    question_text: str
    answer_text: str | None
    passage_text: str


class RagExample(BaseModel):
    score: float
    interview_id: str
    source_file: str
    question_replica_id: int
    question_text: str
    answer_text: str | None


class RagIndexConfig(BaseModel):
    character_id: str
    data_dir: Path
    persist_dir: Path
    manifest_path: Path
    collection_name: str
    model_name: str

    @staticmethod
    def for_character(
        character_id: str,
        cleaned_root: str = "ai_service/data/cleaned",
        indexes_root: str = "ai_service/data/index",
        model_name: str = "intfloat/multilingual-e5-small",
    ) -> "RagIndexConfig":
        data_dir = Path(cleaned_root) / character_id
        base_index_dir = Path(indexes_root) / character_id
        persist_dir = base_index_dir / "chroma"
        manifest_path = base_index_dir / "manifest.json"
        collection_name = f"{character_id}_rag"
        return RagIndexConfig(
            character_id=character_id,
            data_dir=data_dir,
            persist_dir=persist_dir,
            manifest_path=manifest_path,
            collection_name=collection_name,
            model_name=model_name,
        )