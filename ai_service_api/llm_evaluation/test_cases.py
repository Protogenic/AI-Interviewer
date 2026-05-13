from dataclasses import dataclass


@dataclass
class TestCase:
    id: str
    interviewer: str
    emotion: str
    structure: str
    target_words: int
    expected_roles: list[str]
    system_prompt: str
    user_prompt: str


_FMT_SINGLE = (
    "ФОРМАТ ВЫВОДА:\n"
    "Только валидный JSON без markdown, комментариев, без префиксов, без пояснений:\n"
    "{'parts': [{'role': '<role>', 'content': '<one sentence>'}]}\n"
    "- Ровно столько элементов и в том порядке, как задано в поле STRUCTURE пользовательского сообщения.\n"
    "- Каждый content - ровно одно предложение.\n"
    "- Не подписывай реплику именем.\n"
    "# ПРИМЕР КОРРЕКТНОГО ВЫВОДА\n"
    "STRUCTURE: question + acknowledgment\n"
    "{'parts': [{'role': 'question', 'content': 'А ты после этого вообще спал?'},"
    "{'role': 'acknowledgment', 'content': 'Угу.'}]}"
)

_PUNCT = (
    "# ПУНКТУАЦИЯ"
    "Используй: точка, запятая, '?', '!', '...'."
    "Тире '—' и дефис '-' не используй. Вместо тире начинай новое предложение или ставь запятую."
)

_ROLE_QUESTION = (
    "- question - Прямая вопросительная конструкция, нацеленная на получение конкретных фактов, "
    "имен, дат или уточнение обстоятельств события, заканчивается знаком вопроса."
)
_ROLE_ACK = (
    "- acknowledgment - Минимальная реакция, подтверждающая, "
    "что интервьюер слушает гостя и понимает его. Утвердительное или восклицательное предложение."
)
_ROLE_PARAPHRASE = (
    "- paraphrase - сжатый пересказ слов собеседника или подведение итога сказанному, "
    "чтобы подтвердить правильность понимания сути. Утвердительное предложение."
)
_ROLE_BRIDGE = (
    "- bridge - связующая фраза для навигации: смена темы, возврат "
    "к недосказанному или обозначение структуры разговора. Утвердительное предложение."
)
_ROLE_TEXT = (
    "- text - информационное наполнение реплики: изложение фактов, вводных данных "
    "или личного мнения интервьюера, создающее фон для вопроса. Утвердительное предложение."
)
_ROLE_EMPATHY = (
    "- empathy - демонстрация эмоциональной связи: выражение сочувствия, "
    "удивления, поддержки или уместного сомнения в словах гостя. Утвердительное или восклицательное предложение."
)


def _sys_dud(avg_len: int, multi: bool = False) -> str:
    sentence_rule = (
        "Реплика это одно или несколько предложений, "
        "которые могут быть вопросом, утверждением, восклицанием или междометием."
        if multi else
        "Реплика это ровно одно предложение, "
        "которое может быть вопросом, утверждением, восклицанием или междометием."
    )
    return "\n".join([
        "Ты - Юрий Дудь, российский журналист-интервьюер. "
        "Твоя задача - выдать одну реплику этого интервьюера "
        "в соответствии с последним ответом гостя и историей диалога."
        "Стиль интервью: динамичный, прямолинейный, «разговор на равных»."
        "Характерные черты:"
        "- задаёт жёсткие, часто неудобные вопросы, не избегает острых тем"
        "- держит быстрый темп разговора, мало пауз"
        "- активно уточняет и «дожимает», если ответ уклончивый"
        "- старается говорить простым языком, без академичности"
        "# ОБРАЩЕНИЕ Всегда 'ты'. Никогда 'вы'.",
        sentence_rule,
        "# ПЕРСОНА",
        f"Длина: реплика должна быть средней длины (~{avg_len} +- 5 слов). Длина всей реплики не должна превышать эту рамку.",
        _PUNCT,
        "# ОБРАЗЦЫ СТИЛЯ ИНТЕРВЬЮЕРА Это живые цитаты из реальных интервью. Считывай ритм, лексику, степень прямоты:",
        "Подожди, это серьёзно?\n-Ты вообще понимаешь, что происходит?\n-Слушай, давай честно.\n-Ну окей, но зачем?",
        "Не копируй эти фразы дословно. Опирайся на ощущение стиля.",
        _FMT_SINGLE,
    ])


def _sys_sobchak(avg_len: int, multi: bool = False) -> str:
    sentence_rule = (
        "Реплика это одно или несколько предложений, "
        "которые могут быть вопросом, утверждением, восклицанием или междометием."
        if multi else
        "Реплика это ровно одно предложение, "
        "которое может быть вопросом, утверждением, восклицанием или междометием."
    )
    return "\n".join([
        "Ты - Ксения Собчак, российский журналист-интервьюер. "
        "Твоя задача - выдать одну реплику этого интервьюера "
        "в соответствии с последним ответом гостя и историей диалога."
        "Стиль интервью: провокационный, острый, эмоционально заряженный."
        "Характерные черты:"
        "- часто задаёт резкие и провокационные вопросы"
        "- может давить на собеседника психологически"
        "- активно использует сарказм и иронию"
        "# ОБРАЩЕНИЕ Всегда 'ты'. Никогда 'вы'.",
        sentence_rule,
        "# ПЕРСОНА",
        f"Длина: реплика должна быть средней длины (~{avg_len} +- 5 слов). Длина всей реплики не должна превышать эту рамку.",
        _PUNCT,
        "# ОБРАЗЦЫ СТИЛЯ ИНТЕРВЬЮЕРА Это живые цитаты из реальных интервью. Считывай ритм, лексику, степень прямоты:",
        "Ты же понимаешь, что это звучит абсурдно?\n-Ты правда в это веришь?\n-Мне кажется, ты лукавишь.\n-Это очень удобная позиция.",
        "Не копируй эти фразы дословно. Опирайся на ощущение стиля.",
        _FMT_SINGLE,
    ])


def _sys_pozner(avg_len: int, multi: bool = True) -> str:
    sentence_rule = (
        "Реплика это одно или несколько предложений, "
        "которые могут быть вопросом, утверждением, восклицанием или междометием."
        if multi else
        "Реплика это ровно одно предложение, "
        "которое может быть вопросом, утверждением, восклицанием или междометием."
    )
    return "\n".join([
        "Ты - Владимир Познер, российский журналист-интервьюер. "
        "Твоя задача - выдать одну реплику этого интервьюера "
        "в соответствии с последним ответом гостя и историей диалога."
        "Стиль интервью: спокойный, аналитический, интеллигентный."
        "Характерные черты:"
        "-задаёт продуманные, логически выстроенные вопросы"
        "-избегает эмоционального давления на собеседника"
        "-часто переводит разговор в более философскую или социальную плоскость"
        "# ОБРАЩЕНИЕ Всегда 'вы'. Никогда 'ты'.",
        sentence_rule,
        "# ПЕРСОНА",
        f"Длина: реплика развёрнутая, многосоставная (~{avg_len} +- 5 слов)." if avg_len > 25 else
        f"Длина: реплика должна быть средней длины (~{avg_len} +- 5 слов).",
        _PUNCT,
        "# ОБРАЗЦЫ СТИЛЯ ИНТЕРВЬЮЕРА Это живые цитаты из реальных интервью. Считывай ритм, лексику, степень прямоты:",
        "Позвольте спросить вас об этом иначе.\n-Это очень интересная мысль, и она требует уточнения.\n-Как вы сами к этому относитесь?",
        "Не копируй эти фразы дословно. Опирайся на ощущение стиля.",
        _FMT_SINGLE,
    ])


def _user_prompt(
    name: str,
    info: str,
    history: list[tuple[str, str]],
    last_answer: str,
    structure: str,
    action_desc: str,
    emotion_desc: str,
    role_descs: list[str],
    openness: str | None = None,
    techniques: list[str] | None = None,
    examples: list[str] | None = None,
) -> str:
    parts = [
        "# ГОСТЬ",
        f"Имя пользователя: {name}",
        f"Информация о пользователе: {info}",
        "",
        "# ИСТОРИЯ ДИАЛОГА",
    ]
    if not history:
        parts.append("(начало диалога, истории нет)")
    else:
        for role, text in history:
            parts.append(f"{role}: {text}")

    if last_answer:
        parts.append(f"# ПОСЛЕДНЯЯ РЕПЛИКА ГОСТЯ: {last_answer}")

    n_parts = len(structure.split("+"))
    parts += [
        "",
        "# STRUCTURE ДЛЯ ГЕНЕРИРУЕМОЙ РЕПЛИКИ ИНТЕРВЬЮЕРА:",
        f"Роли по порядку: {structure}.",
        f"Реплика состоит РОВНО из {n_parts} предложений.",
        "Значения ролей:",
    ]
    parts.extend(role_descs)
    parts.append(f"- Основное действие фразы: {action_desc}.")
    if openness:
        parts.append(f"- {openness}.")
    parts.append(f"- Эмоциональная окраска: {emotion_desc}.")
    if techniques:
        parts.append("- Используй все или некоторые техники:")
        parts.extend(f"  - {t}" for t in techniques)
    if examples:
        parts.append(f"# ТАК ЗВУЧИТ ЭТОТ ШАБЛОН У ИНТЕРВЬЮЕРА: {', '.join(examples)}")

    return "\n".join(parts)

TEST_CASES: list[TestCase] = [
    TestCase(
        id="dud_01_question_neutral_followup",
        interviewer="dud", emotion="neutral",
        structure="question", target_words=12,
        expected_roles=["question"],
        system_prompt=_sys_dud(12),
        user_prompt=_user_prompt(
            name="Алексей", info="Предприниматель, основатель IT-стартапа",
            history=[
                ("interviewer", "С чего начинался твой первый бизнес?"),
                ("guest", "Мы с другом делали сайты для малого бизнеса, буквально за копейки."),
                ("interviewer", "Когда почувствовал, что это стало серьёзно?"),
                ("guest", "Когда первый крупный клиент заплатил нам за годовой контракт."),
            ],
            last_answer="Первый миллион рублей я заработал в двадцать шесть лет, продав долю в первой компании.",
            structure="question",
            action_desc="задать новый вопрос по другому аспекту темы",
            emotion_desc="нейтральный тон",
            role_descs=[_ROLE_QUESTION],
            openness="Вопрос должен быть открытым",
            techniques=["follow_up - дополнительный вопрос, вытекающий из последнего ответа собеседника."],
        ),
    ),

    TestCase(
        id="dud_02_question_challenge_why",
        interviewer="dud", emotion="challenge",
        structure="question", target_words=12,
        expected_roles=["question"],
        system_prompt=_sys_dud(12),
        user_prompt=_user_prompt(
            name="Дмитрий", info="Топ-менеджер, бывший государственный чиновник",
            history=[
                ("interviewer", "Ты ушёл с поста замминистра в разгар карьеры?"),
                ("guest", "Да, в сорок два года."),
            ],
            last_answer="Я просто уволился в один день, не предупредив никого, даже семью.",
            structure="question",
            action_desc="задать новый вопрос по другому аспекту темы",
            emotion_desc="провокационная, испытывающая",
            role_descs=[_ROLE_QUESTION],
            openness="Вопрос должен быть открытым",
            techniques=["why_question - вопрос 'почему' и похожие."],
        ),
    ),

    TestCase(
        id="dud_03_ack_question_empathy",
        interviewer="dud", emotion="empathy",
        structure="acknowledgment+question", target_words=20,
        expected_roles=["acknowledgment", "question"],
        system_prompt=_sys_dud(12, multi=True),
        user_prompt=_user_prompt(
            name="Мария", info="Спортсменка, олимпийская чемпионка",
            history=[
                ("interviewer", "Когда ты поняла, что больше не сможешь выступать?"),
                ("guest", "После операции на колене врач сказал, что профессиональный спорт закончен."),
                ("interviewer", "Что ты почувствовала в тот момент?"),
                ("guest", "Пустоту. Я не знала, кто я без спорта."),
            ],
            last_answer="Это был самый тяжёлый период в моей жизни, я три месяца не выходила из дома.",
            structure="acknowledgment+question",
            action_desc="задать новый вопрос по другому аспекту темы",
            emotion_desc="сочувствие, эмпатия",
            role_descs=[_ROLE_ACK, _ROLE_QUESTION],
            openness="Вопрос должен быть открытым",
        ),
    ),

    TestCase(
        id="dud_04_question_commentary",
        interviewer="dud", emotion="commentary",
        structure="question", target_words=8,
        expected_roles=["question"],
        system_prompt=_sys_dud(8),
        user_prompt=_user_prompt(
            name="Павел", info="Серийный предприниматель, инвестор",
            history=[
                ("interviewer", "Сколько компаний ты основал?"),
                ("guest", "Семь. Три продал, одна лопнула, три работают."),
            ],
            last_answer="Мне удалось создать команду из пятидесяти человек, которая работает без меня.",
            structure="question",
            action_desc="задать новый вопрос по другому аспекту темы",
            emotion_desc="короткая реакция одобрения на ответ гостя",
            role_descs=[_ROLE_QUESTION],
            openness="Вопрос должен быть закрытым",
        ),
    ),

    TestCase(
        id="dud_05_paraphrase_question_neutral",
        interviewer="dud", emotion="neutral",
        structure="paraphrase+question", target_words=24,
        expected_roles=["paraphrase", "question"],
        system_prompt=_sys_dud(12, multi=True),
        user_prompt=_user_prompt(
            name="Игорь", info="СЕО технологической компании",
            history=[
                ("interviewer", "Как вы выбираете людей в команду?"),
                ("guest", "Я смотрю не на резюме, а на то, как человек думает в нестандартных ситуациях."),
                ("interviewer", "Можешь привести пример?"),
                ("guest", "На последнем собеседовании я попросил кандидата оценить, сколько пианистов в Москве."),
            ],
            last_answer="Важно не правильный ответ, важно как человек рассуждает и справляется с неопределённостью.",
            structure="paraphrase+question",
            action_desc="подытожить или перефразировать для подтверждения",
            emotion_desc="нейтральный тон",
            role_descs=[_ROLE_PARAPHRASE, _ROLE_QUESTION],
            openness="Вопрос должен быть открытым",
        ),
    ),

    TestCase(
        id="dud_06_question_challenge_factcheck",
        interviewer="dud", emotion="challenge",
        structure="question", target_words=10,
        expected_roles=["question"],
        system_prompt=_sys_dud(10),
        user_prompt=_user_prompt(
            name="Роман", info="Основатель финтех-стартапа",
            history=[
                ("interviewer", "Какой у вас сейчас оборот?"),
                ("guest", "Мы выросли на триста процентов за год."),
            ],
            last_answer="Наш продукт используют пять миллионов человек каждый день.",
            structure="question",
            action_desc="уточнить детали или спросить что-то по той же теме",
            emotion_desc="провокационная, испытывающая",
            role_descs=[_ROLE_QUESTION],
            openness="Вопрос должен быть закрытым",
            techniques=["fact_checking - проверка достоверности чего-либо."],
        ),
    ),

    TestCase(
        id="dud_07_bridge_question_transition",
        interviewer="dud", emotion="neutral",
        structure="bridge+question", target_words=22,
        expected_roles=["bridge", "question"],
        system_prompt=_sys_dud(12, multi=True),
        user_prompt=_user_prompt(
            name="Алексей", info="Предприниматель, основатель IT-стартапа",
            history=[
                ("interviewer", "Ты много говорил о победах."),
                ("guest", "Да, были хорошие моменты."),
            ],
            last_answer="В целом я доволен тем, что удалось построить.",
            structure="bridge+question",
            action_desc="перейти к совершенно новой теме, которой нет в истории диалога",
            emotion_desc="нейтральный тон",
            role_descs=[_ROLE_BRIDGE, _ROLE_QUESTION],
            openness="Вопрос должен быть открытым",
        ),
    ),

    TestCase(
        id="sobchak_08_question_challenge",
        interviewer="sobchak", emotion="challenge",
        structure="question", target_words=14,
        expected_roles=["question"],
        system_prompt=_sys_sobchak(14),
        user_prompt=_user_prompt(
            name="Виктор", info="Политик, депутат Государственной думы",
            history=[
                ("interviewer", "Ты голосовал за этот закон?"),
                ("guest", "Ситуация была неоднозначной."),
            ],
            last_answer="Это была вынужденная мера в сложившихся обстоятельствах.",
            structure="question",
            action_desc="уточнить детали или спросить что-то по той же теме",
            emotion_desc="провокационная, испытывающая",
            role_descs=[_ROLE_QUESTION],
            openness="Вопрос должен быть открытым",
            techniques=["why_question - вопрос 'почему' и похожие."],
        ),
    ),

    TestCase(
        id="sobchak_09_question_neutral_transition",
        interviewer="sobchak", emotion="neutral",
        structure="question", target_words=14,
        expected_roles=["question"],
        system_prompt=_sys_sobchak(14),
        user_prompt=_user_prompt(
            name="Анна", info="Телеведущая, медийная личность",
            history=[
                ("interviewer", "Как ты оцениваешь свой путь на телевидении?"),
                ("guest", "Я прошла большой путь от регионального ТВ до федерального."),
                ("interviewer", "Что было сложнее всего?"),
                ("guest", "Сохранять себя под давлением продюсеров."),
            ],
            last_answer="Потом я ушла из эфира и занялась своим YouTube-каналом.",
            structure="question",
            action_desc="перейти к совершенно новой теме, которой нет в истории диалога",
            emotion_desc="нейтральный тон",
            role_descs=[_ROLE_QUESTION],
            openness="Вопрос должен быть открытым",
        ),
    ),

    TestCase(
        id="sobchak_10_ack_question_empathy",
        interviewer="sobchak", emotion="empathy",
        structure="acknowledgment+question", target_words=26,
        expected_roles=["acknowledgment", "question"],
        system_prompt=_sys_sobchak(14, multi=True),
        user_prompt=_user_prompt(
            name="Ольга", info="Актриса, мать троих детей",
            history=[
                ("interviewer", "Ты говорила, что развод дался тебе тяжело."),
                ("guest", "Я не ожидала, что это так ударит по детям."),
            ],
            last_answer="Старший сын полгода не разговаривал со мной после того, как узнал об этом.",
            structure="acknowledgment+question",
            action_desc="задать новый вопрос по другому аспекту темы",
            emotion_desc="сочувствие, эмпатия",
            role_descs=[_ROLE_ACK, _ROLE_QUESTION],
            openness="Вопрос должен быть открытым",
        ),
    ),

    TestCase(
        id="sobchak_11_question_challenge_opinion",
        interviewer="sobchak", emotion="challenge",
        structure="question", target_words=14,
        expected_roles=["question"],
        system_prompt=_sys_sobchak(14),
        user_prompt=_user_prompt(
            name="Сергей", info="Известный блогер, публичная фигура",
            history=[
                ("interviewer", "Ты публично поддержал эту инициативу?"),
                ("guest", "Да, я считаю, что у меня есть социальная ответственность."),
            ],
            last_answer="Я считаю, что это абсолютно правильное решение и не собираюсь его пересматривать.",
            structure="question",
            action_desc="задать новый вопрос по другому аспекту темы",
            emotion_desc="провокационная, испытывающая",
            role_descs=[_ROLE_QUESTION],
            openness="Вопрос должен быть открытым",
            techniques=["opinion_request - о личном взгляде гостя на какую-либо тему."],
        ),
    ),

    TestCase(
        id="sobchak_12_paraphrase_question_neutral",
        interviewer="sobchak", emotion="neutral",
        structure="paraphrase+question", target_words=26,
        expected_roles=["paraphrase", "question"],
        system_prompt=_sys_sobchak(14, multi=True),
        user_prompt=_user_prompt(
            name="Наталья", info="Режиссёр, сценарист",
            history=[
                ("interviewer", "Как ты работаешь над новым проектом?"),
                ("guest", "Я просыпаюсь в пять утра, три часа пишу до завтрака, потом съёмки."),
                ("interviewer", "Каждый день?"),
                ("guest", "Без исключений, даже в выходные."),
            ],
            last_answer="Дисциплина для меня важнее вдохновения, вдохновение приходит в процессе работы.",
            structure="paraphrase+question",
            action_desc="подытожить или перефразировать для подтверждения",
            emotion_desc="нейтральный тон",
            role_descs=[_ROLE_PARAPHRASE, _ROLE_QUESTION],
            openness="Вопрос должен быть открытым",
        ),
    ),

    TestCase(
        id="sobchak_13_question_challenge_factcheck",
        interviewer="sobchak", emotion="challenge",
        structure="question", target_words=14,
        expected_roles=["question"],
        system_prompt=_sys_sobchak(14),
        user_prompt=_user_prompt(
            name="Михаил", info="Инфлюенсер, автор курсов по саморазвитию",
            history=[
                ("interviewer", "Ты говоришь, что твои методы работают для всех?"),
                ("guest", "Я видел тысячи изменившихся жизней."),
            ],
            last_answer="Девяносто восемь процентов моих учеников достигают результата за тридцать дней.",
            structure="question",
            action_desc="уточнить детали или спросить что-то по той же теме",
            emotion_desc="провокационная, испытывающая",
            role_descs=[_ROLE_QUESTION],
            openness="Вопрос должен быть открытым",
            techniques=["fact_checking - проверка достоверности чего-либо."],
        ),
    ),

    TestCase(
        id="sobchak_14_bridge_question_transition",
        interviewer="sobchak", emotion="neutral",
        structure="bridge+question", target_words=26,
        expected_roles=["bridge", "question"],
        system_prompt=_sys_sobchak(14, multi=True),
        user_prompt=_user_prompt(
            name="Анна", info="Телеведущая, медийная личность",
            history=[
                ("interviewer", "Работа занимает у тебя много времени?"),
                ("guest", "Практически всё время, если честно."),
            ],
            last_answer="Я вкладываюсь в карьеру полностью, это мой осознанный выбор.",
            structure="bridge+question",
            action_desc="перейти к совершенно новой теме, которой нет в истории диалога",
            emotion_desc="нейтральный тон",
            role_descs=[_ROLE_BRIDGE, _ROLE_QUESTION],
            openness="Вопрос должен быть открытым",
        ),
    ),

    TestCase(
        id="pozner_15_question_neutral_values",
        interviewer="pozner", emotion="neutral",
        structure="question", target_words=28,
        expected_roles=["question"],
        system_prompt=_sys_pozner(28),
        user_prompt=_user_prompt(
            name="Андрей", info="Философ, профессор МГУ",
            history=[
                ("interviewer", "Как вы определяете для себя понятие счастья?"),
                ("guest", "Счастье для меня связано со смыслом, а не с удовольствием."),
                ("interviewer", "Откуда берётся этот смысл?"),
                ("guest", "Из отношений с людьми, из работы, из принятия конечности жизни."),
            ],
            last_answer="Я пришёл к убеждению, что человек несёт ответственность за смысл своей жизни сам.",
            structure="question",
            action_desc="задать новый вопрос по другому аспекту темы",
            emotion_desc="нейтральный тон",
            role_descs=[_ROLE_QUESTION],
            openness="Вопрос должен быть открытым",
            techniques=["values_exploration - вопрос про отношение и значение чего-то для гостя."],
        ),
    ),

    TestCase(
        id="pozner_16_paraphrase_question_neutral",
        interviewer="pozner", emotion="neutral",
        structure="paraphrase+question", target_words=50,
        expected_roles=["paraphrase", "question"],
        system_prompt=_sys_pozner(28, multi=True),
        user_prompt=_user_prompt(
            name="Евгений", info="Дирижёр, художественный руководитель театра",
            history=[
                ("interviewer", "Как вы пришли к профессии дирижёра?"),
                ("guest", "Через пианино, потом скрипку, потом случайно попал на мастер-класс Темирканова."),
                ("interviewer", "Что изменил этот мастер-класс?"),
                ("guest", "Я понял, что музыкант управляет не нотами, а людьми."),
            ],
            last_answer="Дирижёр это в первую очередь психолог и лидер, а потом уже музыкант.",
            structure="paraphrase+question",
            action_desc="подытожить или перефразировать для подтверждения",
            emotion_desc="нейтральный тон",
            role_descs=[_ROLE_PARAPHRASE, _ROLE_QUESTION],
            openness="Вопрос должен быть открытым",
        ),
    ),

    TestCase(
        id="pozner_17_text_question_opinion",
        interviewer="pozner", emotion="neutral",
        structure="text+question", target_words=50,
        expected_roles=["text", "question"],
        system_prompt=_sys_pozner(28, multi=True),
        user_prompt=_user_prompt(
            name="Ирина", info="Главный редактор федерального издания",
            history=[
                ("interviewer", "Как вы оцениваете состояние журналистики сегодня?"),
                ("guest", "Профессия находится в кризисе доверия."),
            ],
            last_answer="Читатель больше не верит институциям, он верит конкретным людям, авторам.",
            structure="text+question",
            action_desc="задать новый вопрос по другому аспекту темы",
            emotion_desc="нейтральный тон",
            role_descs=[_ROLE_TEXT, _ROLE_QUESTION],
            openness="Вопрос должен быть открытым",
            techniques=["opinion_request - о личном взгляде гостя на какую-либо тему."],
        ),
    ),

    TestCase(
        id="pozner_18_question_neutral_background",
        interviewer="pozner", emotion="neutral",
        structure="question", target_words=28,
        expected_roles=["question"],
        system_prompt=_sys_pozner(28),
        user_prompt=_user_prompt(
            name="Константин", info="Историк, автор книг о советской эпохе",
            history=[
                ("interviewer", "Что, на ваш взгляд, определило характер советского общества?"),
                ("guest", "Страх. Страх был структурообразующим элементом."),
            ],
            last_answer="Реформы Хрущёва были попыткой выйти из этого состояния, но они оказались половинчатыми.",
            structure="question",
            action_desc="задать новый вопрос по другому аспекту темы",
            emotion_desc="нейтральный тон",
            role_descs=[_ROLE_QUESTION],
            openness="Вопрос должен быть открытым",
            techniques=["background_request - изучение контекста, предыстории событий."],
        ),
    ),

    TestCase(
        id="pozner_19_question_empathy",
        interviewer="pozner", emotion="empathy",
        structure="question", target_words=28,
        expected_roles=["question"],
        system_prompt=_sys_pozner(28),
        user_prompt=_user_prompt(
            name="Лариса", info="Писательница, лауреат литературных премий",
            history=[
                ("interviewer", "Вы потеряли мужа несколько лет назад?"),
                ("guest", "Да, мы прожили вместе тридцать семь лет."),
                ("interviewer", "Как вы справлялись?"),
                ("guest", "Писала. Это было единственное, что помогало."),
            ],
            last_answer="Потеря близкого человека меняет что-то необратимо, мир уже не становится прежним.",
            structure="question",
            action_desc="задать новый вопрос по другому аспекту темы",
            emotion_desc="сочувствие, эмпатия",
            role_descs=[_ROLE_QUESTION],
            openness="Вопрос должен быть открытым",
        ),
    ),

    TestCase(
        id="pozner_20_bridge_question_transition",
        interviewer="pozner", emotion="neutral",
        structure="bridge+question", target_words=50,
        expected_roles=["bridge", "question"],
        system_prompt=_sys_pozner(28, multi=True),
        user_prompt=_user_prompt(
            name="Евгений", info="Дирижёр, художественный руководитель театра",
            history=[
                ("interviewer", "Вы говорили об ответственности художника."),
                ("guest", "Да, я убеждён, что искусство несёт социальную функцию."),
            ],
            last_answer="Театр должен задавать обществу вопросы, которые оно не хочет себе задавать.",
            structure="bridge+question",
            action_desc="перейти к совершенно новой теме, которой нет в истории диалога",
            emotion_desc="нейтральный тон",
            role_descs=[_ROLE_BRIDGE, _ROLE_QUESTION],
            openness="Вопрос должен быть открытым",
            techniques=["values_exploration - вопрос про отношение и значение чего-то для гостя."],
        ),
    ),
]
