"""Post-meeting insights: speaker stats, top words, LLM-extracted key moments.

All numeric/aggregation work is done locally (no API calls). The optional
LLM call extracts a handful of "key moments" with timestamps for the AI dashboard.
"""
from __future__ import annotations

import json
import re
from typing import Any

from app.core.config import get_settings
from app.core.logging import get_logger
from app.services.summarization.prompts import Lang, SYSTEM, pick_language

log = get_logger("llm.insights")


# Stop words for KK / RU / EN. Curated to be small but useful for word clouds.
_STOP_KK = {
    "және", "мен", "де", "да", "ма", "ме", "ба", "бе", "па", "пе", "бір", "бар", "жоқ", "осы",
    "сол", "мынау", "анау", "ол", "біз", "сіз", "сен", "мен", "оның", "онда", "бұл", "сонда",
    "емес", "болады", "болды", "керек", "үшін", "соң", "кейін", "шейін", "арқылы",
}
_STOP_RU = {
    "и", "в", "во", "не", "что", "он", "на", "я", "с", "со", "как", "а", "то", "все", "она", "так",
    "его", "но", "да", "ты", "к", "у", "же", "вы", "за", "бы", "по", "только", "ее", "мне", "было",
    "вот", "от", "меня", "еще", "нет", "о", "из", "ему", "теперь", "когда", "даже", "ну", "вдруг",
    "ли", "если", "уже", "или", "ни", "быть", "был", "него", "до", "вас", "нибудь", "опять", "уж",
    "вам", "ведь", "там", "потом", "себя", "ничего", "ей", "может", "они", "тут", "где", "есть",
    "надо", "ней", "для", "мы", "тебя", "их", "чем", "была", "сам", "чтоб", "без", "будто", "чего",
    "раз", "тоже", "себе", "под", "будет", "ж", "тогда", "кто", "этот", "того", "потому", "этого",
    "какой", "совсем", "ним", "здесь", "этом", "один", "почти", "мой", "тем", "чтобы", "нее",
    "сейчас", "были", "куда", "зачем", "всех", "никогда", "можно", "при", "наконец", "два", "об",
    "другой", "хоть", "после", "над", "больше", "тот", "через", "эти", "нас", "про", "всего",
    "них", "какая", "много", "разве", "три", "эту", "моя", "впрочем", "хорошо", "свою", "этой",
    "перед", "иногда", "лучше", "чуть", "том", "нельзя", "такой", "им", "более", "всегда",
    "конечно", "всю", "между", "это", "ещё", "очень", "просто", "может", "давайте", "так",
    "значит", "вообще",
}
_STOP_EN = {
    "the", "a", "an", "and", "or", "but", "if", "while", "is", "are", "was", "were", "be", "been",
    "being", "have", "has", "had", "do", "does", "did", "of", "to", "in", "on", "at", "by", "for",
    "with", "about", "as", "from", "this", "that", "these", "those", "i", "you", "he", "she", "it",
    "we", "they", "them", "his", "her", "its", "our", "their", "me", "him", "us", "what", "which",
    "who", "whom", "where", "when", "why", "how", "not", "no", "yes", "so", "very", "can", "will",
    "would", "should", "could", "may", "might", "must", "shall", "just", "than", "then", "into",
    "out", "up", "down", "off", "over", "under", "again", "more", "most", "some", "any", "all",
    "each", "few", "other", "many", "such", "only", "own", "same", "other", "now",
}
STOP_WORDS = _STOP_KK | _STOP_RU | _STOP_EN

_WORD_RE = re.compile(r"[\w'-]+", re.UNICODE)


def _word_freq(transcript: list[dict[str, Any]], top_n: int = 50, min_len: int = 3) -> list[dict[str, Any]]:
    counts: dict[str, int] = {}
    for seg in transcript:
        text = (seg.get("text") or "").lower()
        for tok in _WORD_RE.findall(text):
            if len(tok) < min_len:
                continue
            if tok in STOP_WORDS:
                continue
            if tok.isdigit():
                continue
            counts[tok] = counts.get(tok, 0) + 1
    return [
        {"word": w, "count": c}
        for w, c in sorted(counts.items(), key=lambda x: x[1], reverse=True)[:top_n]
    ]


def _speaker_stats(
    transcript: list[dict[str, Any]],
    participants: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    label_by_id: dict[str, str] = {}
    if participants:
        for p in participants:
            label_by_id[p.get("id") or ""] = p.get("label") or p.get("id") or "?"

    stats: dict[str, dict[str, Any]] = {}
    for seg in transcript:
        sp = seg.get("speaker") or "SPEAKER_?"
        s, e = int(seg.get("start_time") or 0), int(seg.get("end_time") or 0)
        dur = max(0, e - s)
        text_words = len((seg.get("text") or "").split())
        bucket = stats.setdefault(sp, {
            "id": sp,
            "label": label_by_id.get(sp, sp),
            "speaking_ms": 0,
            "segments": 0,
            "words": 0,
        })
        bucket["speaking_ms"] += dur
        bucket["segments"] += 1
        bucket["words"] += text_words

    total = sum(b["speaking_ms"] for b in stats.values()) or 1
    out = []
    for b in sorted(stats.values(), key=lambda x: x["speaking_ms"], reverse=True):
        out.append({**b, "share": round(b["speaking_ms"] / total, 4)})
    return out


_KEY_MOMENTS_INSTRUCT: dict[Lang, str] = {
    "ru": (
        "Тебе дан транскрипт заседания с тайм-кодами и метками спикеров. "
        "Найди до 6 КЛЮЧЕВЫХ МОМЕНТОВ: решения, разногласия, голосования, важные предложения. "
        "Каждый момент — это краткое (≤140 знаков) описание, привязанное к конкретному месту. "
        "Верни строгий JSON по схеме без преамбулы:\n"
        "{\"moments\":[{\"at_ms\":<int>,\"speaker\":\"<id>\",\"kind\":\"decision|disagreement|vote|proposal|highlight\","
        "\"summary\":\"<≤140 chars>\"}]}\n"
        "Не выдумывай. Если момент не явный — пропусти. Сохраняй порядок по времени."
    ),
    "kk": (
        "Саған тайм-коды бар жиналыс транскрипті берілді. "
        "6-ға дейінгі НЕГІЗГІ СӘТТЕРДІ тап: шешімдер, келіспеушіліктер, дауыс берулер, маңызды ұсыныстар. "
        "Әр сәт — нақты орынға байланған қысқа (≤140 таңба) сипаттама. "
        "Қатаң JSON қайтар (алғы сөзсіз):\n"
        "{\"moments\":[{\"at_ms\":<int>,\"speaker\":\"<id>\",\"kind\":\"decision|disagreement|vote|proposal|highlight\","
        "\"summary\":\"<≤140 таңба>\"}]}\n"
        "Ойдан шығарма, айқын емес болса — өткізіп жібер. Уақыт ретімен сақта."
    ),
    "en": (
        "You are given a meeting transcript with timestamps and speaker labels. "
        "Find up to 6 KEY MOMENTS: decisions, disagreements, votes, important proposals. "
        "Each moment is a short (≤140 char) summary anchored to a specific position. "
        "Return strict JSON with no preamble:\n"
        "{\"moments\":[{\"at_ms\":<int>,\"speaker\":\"<id>\",\"kind\":\"decision|disagreement|vote|proposal|highlight\","
        "\"summary\":\"<≤140 chars>\"}]}\n"
        "Never invent. Skip ambiguous moments. Preserve chronological order."
    ),
}


def _format_for_llm(transcript: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    for seg in transcript:
        ms = int(seg.get("start_time") or 0)
        sp = seg.get("speaker") or "SPEAKER_?"
        lang = seg.get("language") or "?"
        text = (seg.get("text") or "").strip()
        if not text:
            continue
        lines.append(f"[{ms}ms] ({lang}) {sp}: {text}")
    return "\n".join(lines)


def _key_moments(transcript: list[dict[str, Any]], languages: list[str] | None) -> list[dict[str, Any]]:
    if not transcript:
        return []
    settings = get_settings()
    if not settings.openai_api_key:
        return []
    from openai import OpenAI

    lang: Lang = pick_language(languages)
    serialized = _format_for_llm(transcript)
    client = OpenAI(api_key=settings.openai_api_key)
    instructions = f"{SYSTEM[lang]}\n\n{_KEY_MOMENTS_INSTRUCT[lang]}"
    log.info("llm.insights.call", chars=len(serialized), lang=lang)
    try:
        resp = client.responses.create(
            model=settings.llm_model,
            instructions=instructions,
            input=[{"role": "user", "content": serialized}],
        )
    except Exception as e:  # noqa: BLE001
        log.warning("llm.insights.failed", err=str(e))
        return []

    raw = (resp.output_text or "").strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1] if "\n" in raw else ""
        if raw.endswith("```"):
            raw = raw[:-3].rstrip()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        log.warning("llm.insights.bad_json", raw_preview=raw[:200])
        return []
    moments = data.get("moments") if isinstance(data, dict) else None
    if not isinstance(moments, list):
        return []
    out: list[dict[str, Any]] = []
    for m in moments[:6]:
        if not isinstance(m, dict):
            continue
        try:
            out.append({
                "at_ms": int(m.get("at_ms") or 0),
                "speaker": str(m.get("speaker") or ""),
                "kind": str(m.get("kind") or "highlight"),
                "summary": str(m.get("summary") or "")[:200],
            })
        except (TypeError, ValueError):
            continue
    out.sort(key=lambda x: x["at_ms"])
    return out


def build_insights(
    transcript: list[dict[str, Any]],
    participants: list[dict[str, Any]] | None,
    languages: list[str] | None,
    *,
    include_key_moments: bool = True,
) -> dict[str, Any]:
    speakers = _speaker_stats(transcript, participants)
    words = _word_freq(transcript)
    total_ms = sum(s["speaking_ms"] for s in speakers)
    moments = _key_moments(transcript, languages) if include_key_moments else []
    return {
        "speakers": speakers,
        "top_words": words,
        "key_moments": moments,
        "totals": {
            "speaking_ms": total_ms,
            "segments": sum(s["segments"] for s in speakers),
            "speakers": len(speakers),
            "words": sum(s["words"] for s in speakers),
        },
    }


__all__ = ["build_insights"]
