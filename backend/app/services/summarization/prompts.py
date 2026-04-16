"""Prompts in kk/ru/en for meeting-protocol summarization."""
from __future__ import annotations

from typing import Literal

Lang = Literal["kk", "ru", "en"]


SYSTEM: dict[Lang, str] = {
    "ru": (
        "Ты — помощник-секретарь, составляющий официальный протокол заседания. "
        "Отвечай строго на русском языке. Используй только факты из транскрипта; "
        "не выдумывай участников, решения, сроки и цифры. Если данных нет — оставляй поле пустым. "
        "Решение — это явный итог с формулировкой действия (часто с голосованием). "
        "Поручение (action item) — задача с исполнителем и/или дедлайном. "
        "Повестка — перечень рассмотренных тем, в порядке обсуждения."
    ),
    "kk": (
        "Сен — ресми жиналыс хаттамасын құрастыратын хатшы-көмекшісің. "
        "Жауапты тек қазақ тілінде бер. Тек транскриптегі фактілерді пайдалан; "
        "қатысушылар, шешімдер, мерзімдер мен сандарды ойдан шығарма. Дерек болмаса, өрісті бос қалдыр. "
        "Шешім — әрекет тұжырымдалған нақты қорытынды (көбінесе дауыс берумен). "
        "Тапсырма — орындаушы және/немесе мерзімі бар іс. "
        "Күн тәртібі — талқыланған тақырыптардың реттелген тізімі."
    ),
    "en": (
        "You are an assistant secretary producing the official minutes of a meeting. "
        "Answer strictly in English. Use only facts present in the transcript; do not "
        "invent participants, decisions, deadlines or numbers. Leave a field empty when "
        "data is missing. A decision is an explicit resolution with an actionable wording "
        "(often with a vote). An action item is a task with an assignee and/or deadline. "
        "The agenda lists the topics discussed, in order."
    ),
}


MAP_INSTRUCTIONS: dict[Lang, str] = {
    "ru": (
        "Это фрагмент стенограммы заседания. Кратко опиши суть обсуждения, "
        "перечисли упомянутых участников по их меткам (label из transcript), "
        "кандидатов в решения и поручения. Не дублируй — только то, что прозвучало в фрагменте."
    ),
    "kk": (
        "Бұл — жиналыс стенограммасының үзіндісі. Талқылаудың мәнін қысқа сипатта, "
        "аталған қатысушыларды (transcript-тегі label) тізіп шық, "
        "шешім мен тапсырмаға кандидаттарды бөліп көрсет. Тек үзіндіде айтылғанды қосу."
    ),
    "en": (
        "This is a fragment of a meeting transcript. Summarize the discussion, list the "
        "participants mentioned (by their transcript label), and propose candidate decisions "
        "and action items. Only include items actually present in the fragment."
    ),
}


REDUCE_INSTRUCTIONS: dict[Lang, str] = {
    "ru": (
        "Ниже — частичные резюме всех фрагментов заседания. "
        "Собери целостный протокол: заголовок (если явно звучал), дату (если была названа), "
        "повестку (упорядоченную), ключевые темы обсуждения, финальные решения (с голосованием, если было), "
        "и поручения. Объединяй дубли, разрешай противоречия в пользу более позднего упоминания."
    ),
    "kk": (
        "Төменде — жиналыстың әр үзіндісі бойынша жартылай қорытындылар. "
        "Тұтас хаттама жина: тақырып (айқын айтылса), күн (аталса), "
        "күн тәртібі (реттелген), негізгі талқылау тақырыптары, соңғы шешімдер "
        "(дауыс беру болса — санымен) және тапсырмалар. Қайталанатынды біріктір, "
        "қарама-қайшылықта кейінгі нұсқаға басымдық бер."
    ),
    "en": (
        "Below are partial summaries of every fragment of the meeting. "
        "Produce one coherent protocol: title (if explicitly stated), date (if mentioned), "
        "ordered agenda, key discussion topics, final decisions (with vote counts when present), "
        "and action items. Merge duplicates; when conflicting, prefer the later mention."
    ),
}


def pick_language(languages_detected: list[str] | None) -> Lang:
    if not languages_detected:
        return "ru"
    first = languages_detected[0]
    return first if first in ("kk", "ru", "en") else "ru"  # type: ignore[return-value]
