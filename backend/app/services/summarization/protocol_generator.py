"""Single-call protocol generator.

Hands the transcript + chosen template body to OpenAI and expects the
model to return a fully-filled markdown protocol. No structured output,
no map/reduce — the template itself drives the shape.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from app.core.config import get_settings
from app.core.logging import get_logger
from app.services.summarization.prompts import Lang, SYSTEM, pick_language
from app.services.summarization.templates import Template

if TYPE_CHECKING:
    from openai import OpenAI

log = get_logger("llm.protocol")


def _client() -> "OpenAI":
    from openai import OpenAI

    s = get_settings()
    if not s.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured")
    return OpenAI(api_key=s.openai_api_key)


def _format_transcript(transcript: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    for seg in transcript:
        t = int(seg.get("start_time", 0)) // 1000
        mm, ss = divmod(t, 60)
        speaker = seg.get("speaker") or "SPEAKER_?"
        lang = seg.get("language") or "?"
        text = (seg.get("text") or "").strip()
        if not text:
            continue
        lines.append(f"[{mm:02d}:{ss:02d}] ({lang}) {speaker}: {text}")
    return "\n".join(lines)


_INSTRUCT: dict[Lang, str] = {
    "ru": (
        "Тебе даны: (1) транскрипт заседания с тайм-кодами и метками спикеров, "
        "(2) шаблон протокола с плейсхолдерами вида {{var}} и блоками {{#list}}...{{/list}}.\n\n"
        "Задача: вернуть ГОТОВЫЙ markdown-протокол — тот же шаблон, но с подставленными "
        "значениями из транскрипта.\n\n"
        "Правила:\n"
        "— Отвечай только markdown-ом протокола. Без преамбулы, без ```markdown.\n"
        "— Плейсхолдеры заменяй фактами из транскрипта. Не выдумывай имена, даты, цифры.\n"
        "— Если данных для поля нет — оставляй поле пустым (удаляй плейсхолдер), "
        "но сохраняй заголовок секции.\n"
        "— Блок {{#items}}...{{/items}} разворачивай по каждому рассмотренному вопросу. "
        "Если вопросов нет — убери блок целиком.\n"
        "— Голосование указывай только если оно явно прозвучало.\n"
        "— Даты приводи в DD.MM.YYYY, если формат не задан шаблоном иначе.\n"
        "— Сохраняй структуру markdown (заголовки, таблицы, разделители) как в шаблоне."
    ),
    "kk": (
        "Саған берілді: (1) жиналыстың тайм-коды бар транскрипті, "
        "(2) {{var}} және {{#list}}...{{/list}} плейсхолдерлері бар хаттама шаблоны.\n\n"
        "Міндет: дайын markdown хаттаманы қайтар — сол шаблон, бірақ транскриптен алынған "
        "деректермен толтырылған.\n\n"
        "Ереже: тек хаттаманы қайтар, алғы сөзсіз. Плейсхолдерлерді фактілермен алмастыр. "
        "Дерек жоқ болса — өрісті бос қалдыр (плейсхолдерді өшір), бөлім тақырыбын сақта. "
        "Ештеңе ойдан шығарма. Markdown құрылымын сақта."
    ),
    "en": (
        "You are given: (1) a timestamped meeting transcript with speaker labels, "
        "(2) a protocol template with {{var}} placeholders and {{#list}}...{{/list}} blocks.\n\n"
        "Task: return the filled markdown protocol — the same template with placeholders replaced "
        "by facts from the transcript.\n\n"
        "Rules: reply with the markdown protocol only, no preamble, no ```markdown fences. "
        "Replace placeholders with facts from the transcript; never invent names, dates or numbers. "
        "If a field has no data, leave it empty (remove the placeholder) but keep the section heading. "
        "Expand {{#items}}...{{/items}} per discussed item; drop the block if none. "
        "Include vote counts only if explicitly stated. "
        "Preserve the markdown structure (headings, tables, dividers) of the template."
    ),
}


def generate_from_template(
    transcript: list[dict[str, Any]],
    template: Template,
    languages_detected: list[str] | None = None,
) -> str:
    """Call OpenAI once, return the filled markdown protocol as a string."""
    if not transcript:
        return template.body  # nothing to fill — caller decides what to do

    settings = get_settings()
    model = settings.llm_model
    lang: Lang = pick_language(languages_detected)

    serialized = _format_transcript(transcript)
    base = f"{SYSTEM[lang]}\n\n{_INSTRUCT[lang]}"
    # Casual notes can read between the lines (implicit agreements, topics).
    if template.meta.id == "casual" or "casual" in (template.meta.id or ""):
        base += (
            "\n\nДЛЯ ЭТОГО ШАБЛОНА: разговор неформальный. Разрешено делать разумные выводы:"
            " извлекать ТЕМЫ (о чём говорили), УПОМИНАНИЯ (люди/компании/цифры), явные И подразумеваемые"
            " договорённости ('я пришлю завтра' = договорённость), следующие шаги. Если чего-то"
            " действительно нет — убери всю секцию вместе с заголовком."
        )
    instructions = base
    user_msg = (
        f"# ТРАНСКРИПТ / TRANSCRIPT\n\n{serialized}\n\n"
        f"---\n\n"
        f"# ШАБЛОН / TEMPLATE (id={template.meta.id}, name={template.meta.name})\n\n"
        f"{template.body}"
    )

    client = _client()
    log.info(
        "llm.protocol.call",
        template_id=template.meta.id,
        transcript_chars=len(serialized),
        lang=lang,
        model=model,
    )
    resp = client.responses.create(
        model=model,
        instructions=instructions,
        input=[{"role": "user", "content": user_msg}],
    )
    out = (resp.output_text or "").strip()
    # Strip accidental ```markdown fences if the model ignored the rule.
    if out.startswith("```"):
        out = out.split("\n", 1)[1] if "\n" in out else ""
        if out.endswith("```"):
            out = out[: -3].rstrip()
    return out


__all__ = ["generate_from_template"]
