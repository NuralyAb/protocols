"""Jinja2 HTML template for PDF export. WeasyPrint renders this to PDF.

Uses system-installed Noto fonts (installed in Dockerfile). Covers Latin, Cyrillic
and Kazakh letters (ә, ө, ү, ұ, қ, ғ, ң, һ, і).
"""
from __future__ import annotations

from typing import Any

from jinja2 import Environment, select_autoescape

from app.services.export.formatting import (
    ms_to_clock,
    result_title,
    speaker_label,
    speakers_by_id,
)

_env = Environment(autoescape=select_autoescape(["html", "xml"]))

_TEMPLATE = _env.from_string(
    """<!doctype html>
<html lang="{{ lang }}">
<head>
<meta charset="utf-8" />
<title>{{ title }}</title>
<style>
  @page { size: A4; margin: 20mm 18mm; @bottom-right { content: counter(page) " / " counter(pages); font-size: 9pt; color: #777; } }
  * { box-sizing: border-box; }
  body { font-family: "Noto Sans", "Noto Sans Kazakh", sans-serif; color: #111; font-size: 11pt; line-height: 1.45; }
  h1 { font-size: 20pt; margin: 0 0 4pt; }
  h2 { font-size: 13pt; margin: 18pt 0 6pt; border-bottom: 1px solid #bbb; padding-bottom: 2pt; }
  .muted { color: #666; font-size: 9.5pt; }
  .block { margin-bottom: 8pt; }
  table { width: 100%; border-collapse: collapse; font-size: 10pt; }
  th, td { text-align: left; padding: 4pt 6pt; border-bottom: 1px solid #e4e4e4; vertical-align: top; }
  th { background: #f4f4f6; font-weight: 600; }
  ul, ol { margin: 4pt 0 4pt 18pt; padding: 0; }
  li { margin-bottom: 3pt; }
  .ts { color: #888; font-variant-numeric: tabular-nums; }
  .spk { font-weight: 600; }
  .sign { background: #fff7ed; padding: 1pt 4pt; border-radius: 3pt; font-size: 9pt; color: #9a3412; margin-left: 4pt; }
  .votes { font-variant-numeric: tabular-nums; }
</style>
</head>
<body>
  <h1>{{ title }}</h1>
  {% if date %}<div class="muted">{{ labels.date }}: {{ date }}</div>{% endif %}
  <div class="muted">{{ labels.duration }}: {{ duration }} • {{ labels.languages }}: {{ languages|join(', ') or '—' }}</div>

  <h2>{{ labels.participants }}</h2>
  {% if participants %}
  <table>
    <thead><tr><th>{{ labels.p_label }}</th><th>{{ labels.p_role }}</th></tr></thead>
    <tbody>
      {% for p in participants %}
      <tr>
        <td>{{ p.label or p.id }}</td>
        <td>{{ p.role or '—' }}</td>
      </tr>
      {% endfor %}
    </tbody>
  </table>
  {% else %}<p class="muted">—</p>{% endif %}

  {% if agenda %}
  <h2>{{ labels.agenda }}</h2>
  <ol>{% for item in agenda %}<li>{{ item }}</li>{% endfor %}</ol>
  {% endif %}

  {% if discussion %}
  <h2>{{ labels.discussion }}</h2>
  {% for d in discussion %}
    <div class="block">
      <strong>{{ d.topic }}</strong>
      <div>{{ d.summary }}</div>
      {% if d.speakers %}<div class="muted">{{ labels.speakers }}: {{ d.speakers|join(', ') }}</div>{% endif %}
    </div>
  {% endfor %}
  {% endif %}

  {% if decisions %}
  <h2>{{ labels.decisions }}</h2>
  <ol>
    {% for dec in decisions %}
    <li>
      {{ dec.text }}
      {% if dec.votes %}
        <span class="votes">({{ labels.v_for }}: {{ dec.votes['for'] or 0 }} · {{ labels.v_against }}: {{ dec.votes.against or 0 }} · {{ labels.v_abstain }}: {{ dec.votes.abstain or 0 }})</span>
      {% endif %}
    </li>
    {% endfor %}
  </ol>
  {% endif %}

  {% if action_items %}
  <h2>{{ labels.actions }}</h2>
  <table>
    <thead><tr><th>{{ labels.a_task }}</th><th>{{ labels.a_assignee }}</th><th>{{ labels.a_deadline }}</th></tr></thead>
    <tbody>
      {% for a in action_items %}
      <tr><td>{{ a.task }}</td><td>{{ a.assignee or '—' }}</td><td>{{ a.deadline or '—' }}</td></tr>
      {% endfor %}
    </tbody>
  </table>
  {% endif %}

  <h2>{{ labels.transcript }}</h2>
  {% for s in transcript %}
    <div class="block">
      <span class="ts">[{{ s.clock }}]</span>
      <span class="spk">{{ s.label }}</span>
      {% if s.lang %}<span class="muted"> · {{ s.lang }}</span>{% endif %}
      <div>{{ s.text }}</div>
    </div>
  {% endfor %}
</body>
</html>
"""
)


LABELS: dict[str, dict[str, str]] = {
    "ru": {
        "date": "Дата", "duration": "Длительность", "languages": "Языки",
        "participants": "Участники", "agenda": "Повестка", "discussion": "Ход обсуждения",
        "decisions": "Принятые решения", "actions": "Поручения", "transcript": "Стенограмма",
        "speakers": "Говорили",
        "p_label": "Участник", "p_role": "Роль",
        "v_for": "за", "v_against": "против", "v_abstain": "воздержались",
        "a_task": "Задача", "a_assignee": "Исполнитель", "a_deadline": "Срок",
    },
    "kk": {
        "date": "Күні", "duration": "Ұзақтығы", "languages": "Тілдер",
        "participants": "Қатысушылар", "agenda": "Күн тәртібі", "discussion": "Талқылау барысы",
        "decisions": "Қабылданған шешімдер", "actions": "Тапсырмалар", "transcript": "Стенограмма",
        "speakers": "Сөйлегендер",
        "p_label": "Қатысушы", "p_role": "Рөлі",
        "v_for": "жақтап", "v_against": "қарсы", "v_abstain": "қалыс",
        "a_task": "Тапсырма", "a_assignee": "Орындаушы", "a_deadline": "Мерзімі",
    },
    "en": {
        "date": "Date", "duration": "Duration", "languages": "Languages",
        "participants": "Participants", "agenda": "Agenda", "discussion": "Discussion",
        "decisions": "Decisions", "actions": "Action items", "transcript": "Transcript",
        "speakers": "Speakers",
        "p_label": "Participant", "p_role": "Role",
        "v_for": "for", "v_against": "against", "v_abstain": "abstained",
        "a_task": "Task", "a_assignee": "Assignee", "a_deadline": "Deadline",
    },
}


def _pick_lang(result: dict[str, Any]) -> str:
    langs = (result.get("metadata") or {}).get("languages_detected") or []
    for c in langs:
        if c in LABELS:
            return c
    return "ru"


def _format_duration(ms: int) -> str:
    sec = int(ms // 1000)
    h, m = divmod(sec // 60, 60)
    s = sec % 60
    return f"{h:02d}:{m:02d}:{s:02d}"


def render_html(result: dict[str, Any]) -> str:
    lang = _pick_lang(result)
    proto = result.get("protocol") or {}
    meta = result.get("metadata") or {}
    spk_map = speakers_by_id(result)

    transcript = []
    for s in result.get("transcript") or []:
        start = int(s.get("start_time") or 0)
        transcript.append(
            {
                "clock": ms_to_clock(start),
                "label": speaker_label(s.get("speaker", ""), spk_map),
                "text": s.get("text") or "",
                "lang": s.get("language"),
                "modality": s.get("input_modality") or "speech",
            }
        )

    return _TEMPLATE.render(
        lang=lang,
        title=result_title(result, {"ru": "Протокол заседания", "kk": "Жиналыс хаттамасы", "en": "Meeting minutes"}[lang]),
        date=proto.get("date"),
        duration=_format_duration(int(meta.get("duration_ms") or 0)),
        languages=meta.get("languages_detected") or [],
        participants=proto.get("participants") or [],
        agenda=proto.get("agenda") or [],
        discussion=proto.get("discussion") or [],
        decisions=proto.get("decisions") or [],
        action_items=proto.get("action_items") or [],
        transcript=transcript,
        labels=LABELS[lang],
    )
