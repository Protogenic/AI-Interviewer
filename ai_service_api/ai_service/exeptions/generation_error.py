class GenerationError(Exception):
    pass

class CharacterNotFound(GenerationError):
    """Ошибка: подражаемый интервьюер не найден в базе"""
    def __init__(self, character_id: str):
        self.__character_id = character_id
        self.__message = f"Character don't exist in database."
        super().__init__(self.__message)