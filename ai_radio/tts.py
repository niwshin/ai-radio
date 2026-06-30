from __future__ import annotations

import subprocess
import wave
from pathlib import Path

import httpx


class VoicevoxSynthesizer:
    def __init__(self, base_url: str, speaker: int, audio_dir: Path):
        self.base_url = base_url.rstrip("/")
        self.speaker = speaker
        self.audio_dir = audio_dir
        self.audio_dir.mkdir(parents=True, exist_ok=True)

    async def synthesize_program(self, program_id: str, text: str) -> Path:
        chunks = split_text(text, max_chars=900)
        wav_paths: list[Path] = []
        async with httpx.AsyncClient(timeout=120.0) as client:
            for idx, chunk in enumerate(chunks):
                query_resp = await client.post(
                    f"{self.base_url}/audio_query",
                    params={"speaker": self.speaker, "text": chunk},
                )
                query_resp.raise_for_status()
                synth_resp = await client.post(
                    f"{self.base_url}/synthesis",
                    params={"speaker": self.speaker},
                    json=query_resp.json(),
                )
                synth_resp.raise_for_status()
                wav_path = self.audio_dir / f"{program_id}_{idx:03d}.wav"
                wav_path.write_bytes(synth_resp.content)
                wav_paths.append(wav_path)

        output = self.audio_dir / f"{program_id}.mp3"
        concat_wavs(wav_paths, self.audio_dir / f"{program_id}.wav")
        wav_concat = self.audio_dir / f"{program_id}.wav"
        subprocess.run(
            ["ffmpeg", "-y", "-i", str(wav_concat), "-filter:a", "loudnorm", str(output)],
            check=True,
            capture_output=True,
        )
        wav_concat.unlink(missing_ok=True)
        for path in wav_paths:
            path.unlink(missing_ok=True)
        return output


def split_text(text: str, max_chars: int) -> list[str]:
    parts: list[str] = []
    current = ""
    for sentence in text.replace("\r\n", "\n").split("。"):
        sentence = sentence.strip()
        if not sentence:
            continue
        candidate = f"{sentence}。"
        if len(current) + len(candidate) > max_chars and current:
            parts.append(current)
            current = candidate
        else:
            current += candidate
    if current:
        parts.append(current)
    return parts or [text[:max_chars]]


def concat_wavs(inputs: list[Path], output: Path) -> None:
    if not inputs:
        raise ValueError("no wav inputs")
    with wave.open(str(inputs[0]), "rb") as first:
        params = first.getparams()
    with wave.open(str(output), "wb") as out:
        out.setparams(params)
        for path in inputs:
            with wave.open(str(path), "rb") as wav:
                if wav.getparams()[:3] != params[:3]:
                    raise ValueError("wav params mismatch")
                frames = wav.readframes(wav.getnframes())
                out.writeframes(frames)
