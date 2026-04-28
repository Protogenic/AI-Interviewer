class TtsError(Exception):
    pass

class VoiceNotFound(TtsError):
    """Ошибка: запрошенный голос не найден в каталоге голосов"""
    def __init__(self, voice_id: str):
        self.__voice_id = voice_id
        self.__message = f"Voice '{voice_id}' don't exist in catalog."
        super().__init__(self.__message)

class UnknownEngine(TtsError):
    """Ошибка: указан неизвестный TTS-движок"""
    def __init__(self, engine: str):
        self.__engine = engine
        self.__message = f"Unknown TTS engine: '{engine}'."
        super().__init__(self.__message)
