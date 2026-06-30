from ai_radio.tts import split_text


def test_split_text_keeps_sentences_under_limit():
    chunks = split_text("これはテストです。次の文です。最後です。", max_chars=12)
    assert chunks
    assert all(chunk.endswith("。") for chunk in chunks)
