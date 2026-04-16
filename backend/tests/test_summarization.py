"""Tests for summarization helpers (chunking, merging, prompt routing) — no network."""
from unittest.mock import MagicMock, patch

from app.services.summarization.llm_service import (
    MAX_CHARS_PER_CHUNK,
    _chunk,
    _format_transcript,
    merge_into_result,
    summarize,
)
from app.services.summarization.prompts import pick_language
from app.services.summarization.schemas import (
    ActionItem,
    Decision,
    DiscussionTopic,
    ProtocolDraft,
    VoteCount,
)


def test_format_transcript_groups_meta() -> None:
    t = _format_transcript(
        [
            {"speaker": "SPEAKER_00", "language": "kk", "start_time": 0, "end_time": 1000, "text": "Сәлем"},
            {"speaker": "SPEAKER_01", "language": "ru", "start_time": 60000, "end_time": 62000, "text": "Привет"},
            {"speaker": "SPEAKER_00", "language": "kk", "start_time": 63000, "end_time": 64000, "text": "   "},
        ]
    )
    assert "[00:00] (kk) SPEAKER_00: Сәлем" in t
    assert "[01:00] (ru) SPEAKER_01: Привет" in t
    assert "SPEAKER_00:   " not in t  # empty text skipped


def test_chunk_respects_budget() -> None:
    lines = "\n".join([f"[00:{i:02d}] (ru) SPK: " + ("x" * 200) for i in range(200)])
    chunks = _chunk(lines, max_chars=1000)
    assert len(chunks) > 1
    for c in chunks:
        assert len(c) <= MAX_CHARS_PER_CHUNK
    assert "".join(chunks).replace("\n", "") == lines.replace("\n", "")


def test_pick_language_defaults_to_ru() -> None:
    assert pick_language(None) == "ru"
    assert pick_language([]) == "ru"
    assert pick_language(["kk", "ru"]) == "kk"
    assert pick_language(["xx"]) == "ru"


def test_vote_count_alias_roundtrip() -> None:
    v = VoteCount(**{"for": 5, "against": 1, "abstain": 0})
    assert v.for_ == 5
    dumped = v.model_dump(by_alias=True)
    assert dumped["for"] == 5


def test_merge_into_result_preserves_transcript() -> None:
    result = {
        "transcript": [{"speaker": "SPEAKER_00", "text": "hi"}],
        "protocol": {"participants": [{"id": "SPEAKER_00"}], "agenda": []},
        "metadata": {"model_versions": {"asr": "large-v3"}},
    }
    draft = ProtocolDraft(
        title="Совещание",
        agenda=["Бюджет", "Кадры"],
        discussion=[DiscussionTopic(topic="Бюджет", summary="...", speakers=["SPEAKER_00"])],
        decisions=[Decision(text="Утвердить", votes=VoteCount(**{"for": 3, "against": 0, "abstain": 1}))],
        action_items=[ActionItem(task="Подготовить отчёт", assignee="SPEAKER_00", deadline="2026-05-01")],
    )
    with patch("app.services.summarization.llm_service.get_settings") as gs:
        gs.return_value = MagicMock(llm_model="gpt-4o")
        merged = merge_into_result(result, draft)
    assert merged["transcript"][0]["text"] == "hi"  # untouched
    assert merged["protocol"]["title"] == "Совещание"
    assert merged["protocol"]["agenda"] == ["Бюджет", "Кадры"]
    assert merged["protocol"]["decisions"][0]["votes"]["for"] == 3
    assert merged["protocol"]["participants"] == [{"id": "SPEAKER_00"}]  # preserved
    assert merged["metadata"]["model_versions"]["summarizer"] == "gpt-4o"


def test_summarize_single_pass_uses_reduce_prompt() -> None:
    transcript = [
        {"speaker": "SPEAKER_00", "language": "ru", "start_time": 0, "end_time": 3000, "text": "Открываем заседание"},
        {"speaker": "SPEAKER_01", "language": "ru", "start_time": 3000, "end_time": 6000, "text": "Предлагаю утвердить бюджет"},
    ]
    fake = ProtocolDraft(agenda=["Бюджет"], decisions=[Decision(text="Утвердить бюджет")])
    fake_client = MagicMock()
    fake_client.responses.parse.return_value = MagicMock(output_parsed=fake)

    with (
        patch("app.services.summarization.llm_service._client", return_value=fake_client),
        patch("app.services.summarization.llm_service.get_settings") as gs,
    ):
        gs.return_value = MagicMock(llm_model="gpt-4o", openai_api_key="sk-test")
        draft = summarize(transcript, languages_detected=["ru"])

    assert draft.agenda == ["Бюджет"]
    assert draft.decisions[0].text == "Утвердить бюджет"
    fake_client.responses.parse.assert_called_once()
    _, kwargs = fake_client.responses.parse.call_args
    assert "ProtocolDraft" in str(kwargs.get("text_format"))
