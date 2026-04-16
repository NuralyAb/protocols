"""Exporter tests — no network, no WeasyPrint (PDF tested separately)."""
from app.services.export.formatting import ms_to_clock, ms_to_timestamp
from app.services.export.html_template import render_html
from app.services.export.plain import render_json, render_txt
from app.services.export.subtitles import render_srt, render_vtt


SAMPLE = {
    "transcript": [
        {
            "speaker": "SPEAKER_00",
            "language": "kk",
            "input_modality": "speech",
            "start_time": 0,
            "end_time": 3200,
            "text": "Сәлем, әріптестер. Жиналысты ашамыз.",
        },
        {
            "speaker": "SPEAKER_01",
            "language": "ru",
            "input_modality": "speech",
            "start_time": 3500,
            "end_time": 6800,
            "text": "Предлагаю утвердить бюджет",
        },
    ],
    "protocol": {
        "title": "Еженедельное заседание",
        "date": "2026-04-15",
        "participants": [
            {"id": "SPEAKER_00", "label": "Айжан", "role": "Председатель"},
            {"id": "SPEAKER_01", "label": "Максим", "role": "Секретарь"},
        ],
        "agenda": ["Бюджет", "Кадры"],
        "discussion": [
            {"topic": "Бюджет", "summary": "Обсуждение квартального бюджета.", "speakers": ["Айжан", "Максим"]}
        ],
        "decisions": [
            {"text": "Утвердить бюджет", "votes": {"for": 3, "against": 0, "abstain": 1}, "speakers": []}
        ],
        "action_items": [
            {"task": "Подготовить отчёт", "assignee": "Максим", "deadline": "2026-05-01"}
        ],
    },
    "metadata": {
        "duration_ms": 6800,
        "languages_detected": ["kk", "ru"],
        "model_versions": {"asr": "large-v3"},
    },
}


def test_timestamp_formats() -> None:
    assert ms_to_timestamp(0) == "00:00:00,000"
    assert ms_to_timestamp(3_723_456) == "01:02:03,456"
    assert ms_to_timestamp(3_723_456, ".") == "01:02:03.456"
    assert ms_to_clock(0) == "00:00"
    assert ms_to_clock(3_600_000) == "01:00:00"


def test_render_srt_contains_speakers_and_cues() -> None:
    data = render_srt(SAMPLE).decode("utf-8")
    assert "1\n00:00:00,000 --> 00:00:03,200" in data
    assert "Айжан (Председатель): Сәлем" in data
    assert "Максим (Секретарь):" in data


def test_render_vtt_uses_voice_tag() -> None:
    data = render_vtt(SAMPLE).decode("utf-8")
    assert data.startswith("WEBVTT\n")
    assert "<v Айжан (Председатель)>Сәлем" in data
    assert "00:00:03.500 --> 00:00:06.800" in data


def test_render_txt_has_all_sections() -> None:
    data = render_txt(SAMPLE).decode("utf-8")
    # Kazakh-dominant → kk labels
    for marker in ["Күн тәртібі", "Қатысушылар", "Қабылданған шешімдер",
                   "Тапсырмалар", "Стенограмма", "жақтап"]:
        assert marker in data
    assert "Бюджет" in data and "Кадры" in data
    assert "Подготовить отчёт" in data


def test_render_json_roundtrip() -> None:
    import json

    data = render_json(SAMPLE)
    parsed = json.loads(data)
    assert parsed["protocol"]["title"] == "Еженедельное заседание"
    assert parsed["transcript"][0]["text"].startswith("Сәлем")


def test_render_html_includes_kazakh_labels() -> None:
    html = render_html(SAMPLE)
    assert "Сәлем" in html
    assert "Күн тәртібі" in html  # kk agenda label
    assert "Максим (Секретарь)" in html


def test_render_txt_handles_empty_result() -> None:
    empty = {"transcript": [], "protocol": {}, "metadata": {}}
    # shouldn't crash; must contain transcript section
    out = render_txt(empty).decode("utf-8")
    assert "Стенограмма" in out or "Transcript" in out or "Стенограмма".lower() in out.lower()


def test_render_docx_is_valid_zip() -> None:
    from zipfile import ZipFile
    from io import BytesIO
    from app.services.export.docx_ import render_docx

    blob = render_docx(SAMPLE)
    # DOCX is a ZIP; check it opens and has the main document part
    with ZipFile(BytesIO(blob)) as zf:
        names = zf.namelist()
        assert "word/document.xml" in names
        body = zf.read("word/document.xml").decode("utf-8")
        assert "Еженедельное заседание" in body
        assert "Подготовить отчёт" in body
