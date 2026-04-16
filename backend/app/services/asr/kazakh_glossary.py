"""Initial-prompt glossary to bias Whisper toward meeting / legal vocabulary.

Per-language prompts reduce WER on proper nouns and domain terms, especially for Kazakh
where the base Whisper is weaker.
"""

KAZAKH_PROMPT = (
    "Жиналыс хаттамасы. Күн тәртібі, төраға, хатшы, баяндамашы, қатысушы. "
    "Шешім қабылданды, жақтап, қарсы, қалыс қалды. Дауыс беру нәтижелері. "
    "Қазақстан Республикасы, министрлік, заң, ереже."
)

RUSSIAN_PROMPT = (
    "Протокол заседания. Повестка дня, председатель, секретарь, докладчик, участник. "
    "Решение принято, за, против, воздержались. Итоги голосования. "
    "Российская Федерация, Республика Казахстан, министерство, закон, регламент."
)

ENGLISH_PROMPT = (
    "Meeting minutes. Agenda, chair, secretary, speaker, participant. "
    "Motion, seconded, in favor, opposed, abstained. Vote results. "
    "Resolution, decision, action item, deadline."
)


def prompt_for(language: str | None) -> str | None:
    match language:
        case "kk":
            return KAZAKH_PROMPT
        case "ru":
            return RUSSIAN_PROMPT
        case "en":
            return ENGLISH_PROMPT
        case _:
            return None
