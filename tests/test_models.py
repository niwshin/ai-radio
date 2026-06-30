from ai_radio.models import ScriptOutput


def test_script_output_validation():
    payload = {
        "topic_title": "AIガジェットの今週",
        "tags": ["AI", "ガジェット"],
        "topic_era": "2026年夏",
        "script": "あ" * 100,
        "segments": [{"title": "導入", "script": "こんにちは"}],
        "sources": [{"title": "source", "url": "https://example.com", "published_at": None, "used_for": "概要"}],
        "voicevox_text": "あ" * 100,
    }
    assert ScriptOutput.model_validate(payload).topic_title == "AIガジェットの今週"
